# -*- coding: utf-8 -*-
from telegram import Chat
from marvinbot.utils import localized_date, trim_accents, get_message
from marvinbot.handlers import CommandHandler, MessageHandler, CommonFilters
from telegram.error import BadRequest
from marvinbot.plugins import Plugin
from topic_plugin.models import Topic, Subtopic
import logging

log = logging.getLogger(__name__)


class TopicPlugin(Plugin):
    def __init__(self):
        super(TopicPlugin, self).__init__('topic_plugin')

    def get_default_config(self):
        return {
            'short_name': self.name,
            'enabled': True,
        }

    def configure(self, config):
        pass

    def setup_handlers(self, adapter):
        log.info("Setting up handlers for Topic plugin")
        self.add_handler(CommandHandler('topic', self.on_topic_command, command_description='Allows the user to control the topic on the chat title.')
                         .add_argument('--set', help='Set the topic', action='store_true')
                         .add_argument('--unset', help='Unset the topic', action='store_true')
                         .add_argument('--pop', help='Pop the subtopic off the end', action='store_true')
                         .add_argument('--push', help='Push a subtopic onto the end', action='store_true')
                         .add_argument('--shift', help='Shift the subtopic from the beginning', action='store_true')
                         .add_argument('--unshift', help='Prepend a subtopic to the beginning', action='store_true')
                         .add_argument('--fix', help='Fix chat title', action='store_true')
                         .add_argument('--pop-all', help='Remove all subtopics', action='store_true'))

        # TODO: Fix chat topic is somebody else sets something
        self.add_handler(MessageHandler([CommonFilters.status_update.new_chat_title], self.on_new_chat_title))
        self.add_handler(MessageHandler([CommonFilters.status_update.left_chat_member], self.on_left_chat_member))

    @classmethod
    def get_topic(cls, chat_id):
        return Topic.by_chat_id(chat_id)

    def on_new_chat_title(self, update):
        topic = self.get_topic(update.effective_chat.id)
        if topic:
            self.set_chat_title_from_topic(topic)
            self.adapter.bot.sendMessage(chat_id=topic.chat_id,
                                         reply_to_message_id=update.effective_message.message_id,
                                         text="❌ Use /topic to change the chat title.")

    def on_left_chat_member(self, update):
        if update.effective_message.left_chat_member.id == self.adapter.bot_info.id:
            topic = self.get_topic(update.effective_chat.id)
            if topic is not None:
                topic.delete()

    def set_chat_title_from_topic(self, topic):
        text = topic.text
        separator = topic.separator
        subtopics = separator.join([subtopic.text for subtopic in topic.subtopics])
        log.debug('Subtopics:',str(topic.subtopics))
        if (len(topic.subtopics)):
            text = "{}{}{}".format(text, separator, subtopics)

        try:
            self.adapter.bot.setChatTitle(chat_id=topic.chat_id, title=topic.text)
            return True
        except BadRequest as ex:
            self.adapter.bot.sendMessage(chat_id=topic.chat_id, text="❌ {}".format(ex))
            return False


    def initialize_topic(self, chat_id, topic, message, user_id, username):
        chat = self.adapter.bot.getChat(chat_id=chat_id)
        if chat.type == Chat.PRIVATE:
            self.adapter.bot.sendMessage(chat_id=chat_id, text="❌ This command does not work in private chats.")
            return None

        same = message.text == chat.title

        text = chat.title

        try:
            topic = Topic(chat_id=message.chat_id, text=text, subtopics=[], user_id=user_id, username=username)
            if self.set_chat_title_from_topic(topic) or same:
                topic.save()
                return topic
            return None
        except BadRequest as ex:
            self.adapter.bot.sendMessage(chat_id=chat_id, text="❌ {}".format(ex))
            return None

    def on_topic_set(self, chat_id, topic, topic_text, user_id, username):
        topic.text = topic_text
        topic.user_id = user_id
        topic.username = username
        if self.set_chat_title_from_topic(topic):
            topic.save()
            return topic

    def on_subtopic_pop(self, chat_id, topic):
        self.adapter.bot.sendMessage(chat_id=chat_id, text="⚠ Should pop the subtopic off the end")
        subtopic = topic.subtopics.pop()
        subtopic.delete()
        if self.set_chat_title_from_topic(topic):
            topic.save()

    def on_subtopic_push(self, chat_id, topic, subtopic_text, user_id, username):
        self.adapter.bot.sendMessage(chat_id=chat_id, text="⚠ Should push a subtopic onto the end with text {}".format(subtopic_text))
        config = {
            "chat_id": chat_id,
            "text": subtopic_text,
            "user_id": user_id,
            "username": username
        }
        subtopic = Subtopic(**config)

        topic.subtopics.append(subtopic)
        if self.set_chat_title_from_topic(topic):
            subtopic.save()
            topic.save(cascade=True)

    def on_subtopic_shift(self, chat_id, topic):
        self.adapter.bot.sendMessage(chat_id=chat_id, text="⚠ Should shift the subtopic from the beginning")
        subtopic = topic.subtopics[1:]
        if self.set_chat_title_from_topic(topic):
            topic.save()
            subtopic.delete()

    def on_subtopic_unshift(self, chat_id, topic, subtopic_text, user_id, username):
        self.adapter.bot.sendMessage(chat_id=chat_id, text="⚠ Should prepend a subtopic to the beginning with text {}".format(subtopic_text))
        config = {
            "chat_id": chat_id,
            "text": subtopic_text,
            "user_id": user_id,
            "username": username
        }
        subtopic = Subtopic(**config)

        topic.subtopics = [subtopic] + topic.subtopics
        if self.set_chat_title_from_topic(topic):
            subtopic.save()
            subtopic.save(cascade=True)

    def on_subtopic_pop_all(self, chat_id, topic):
        self.adapter.bot.sendMessage(chat_id=chat_id, text="⚠ Should remove all subtopics")
        subtopics = topic.subtopics
        topic.subtopics = []
        if self.set_chat_title_from_topic(topic):
            topic.save()
            for subtopic in subtopics:
                subtopic.delete()


    def on_topic_command(self, update, *args, **kwargs):
        message = update.effective_message
        chat_id = update.effective_chat.id

        set = kwargs.get('set', False)
        unset = kwargs.get('unset', False)
        pop = kwargs.get('pop', False)
        push = kwargs.get('push', False)
        unshift = kwargs.get('unshift', False)
        shift = kwargs.get('shift', False)
        fix = kwargs.get('fix', False)

        user_id = update.effective_user.id
        username = update.effective_user.username

        topic = TopicPlugin.get_topic(chat_id)

        if not topic and not set:
            message.reply_text(text="❌ You need to set a topic first.")
            return

        if fix:
            self.set_chat_title_from_topic(topic)
            return

        if set:
            if not topic:
                topic = self.initialize_topic(chat_id, topic, message, user_id, username)

            if not message.reply_to_message or not message.reply_to_message.text:
                message.reply_text(text="❌ Use --set when replying to a message containing text.")
                return

            topic_text = message.reply_to_message.text
            self.on_topic_set(chat_id, topic, topic_text, user_id, username)

        elif unset:
            topic.delete()
            message.reply_text(text="❌ Topic has been unset.")

        elif shift:
            if len(topic.subtopics) == 0:
                message.reply_text(text="❌ There are no subtopics to shift off.")
                return
            self.on_subtopic_shift(chat_id, topic)

        elif unshift:
            if not message.reply_to_message or not message.reply_to_message.text:
                message.reply_text(text="❌ Use --unshift when replying to a message containing text.")
                return

            # TODO: Check if there's not a subtopic with this text
            subtopic_text = message.reply_to_message.text
            self.on_subtopic_unshift(chat_id, topic, subtopic_text, user_id, username)

        elif pop:
            if len(topic.subtopics) == 0:
                message.reply_text(text="❌ There are no subtopics to pop off.")
                return
            self.on_subtopic_pop(chat_id, topic)

        elif push:
            if not message.reply_to_message or not message.reply_to_message.text:
                message.reply_text(text="❌ Use --push when replying to a message containing text.")
                return

            # TODO: Check if there's not a subtopic with this text
            subtopic_text = message.reply_to_message.text
            self.on_subtopic_push(chat_id, topic, subtopic_text, user_id, username)
