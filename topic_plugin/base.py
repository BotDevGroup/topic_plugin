# -*- coding: utf-8 -*-
from telegram import Chat
from marvinbot.utils import localized_date, trim_accents, get_message
from marvinbot.handlers import CommandHandler
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
                         .add_argument('--pop', help='Pop the subtopic off the end', action='store_true')
                         .add_argument('--push', help='Push a subtopic onto the end', action='store_true')
                         .add_argument('--shift', help='Shift the subtopic from the beginning', action='store_true')
                         .add_argument('--unshift', help='Prepend a subtopic to the beginning', action='store_true')
                         .add_argument('--init', help='Initialize plugin', action='store_true')
                         .add_argument('--fix', help='Fix chat title', action='store_true')
                         .add_argument('--pop-all', help='Remove all subtopics', action='store_true'))

    def setup_schedules(self, adapter):
        pass

    @classmethod
    def get_topic(cls, chat_id):
        return Topic.by_chat_id(chat_id)

    def set_topic(self, topic):
        text = topic.text
        separator = topic.separator
        subtopics = separator.join([subtopic.text for subtopic in topic.subtopics])
        if (len(topic.subtopics)):
            text = "{}{}{}".format(text, separator, subtopics)
        self.adapter.bot.setChatTitle(chat_id=topic.chat_id, title=topic.text)
        self.adapter.bot.sendMessage(chat_id=topic.chat_id, text="Topic set to {}".format(text))

    def initialize_topic(self, chat_id, topic, message):
        if topic is not None:
            self.adapter.bot.sendMessage(chat_id=chat_id, text="❌ Already initialized")
        else:
            chat = self.adapter.bot.getChat(chat_id=chat_id)
            if chat.type == Chat.PRIVATE:
                self.adapter.bot.sendMessage(chat_id=chat_id, text="❌ This command does not work in private chats.")
                return

            text = chat.title
            if message.reply_to_message:
                text = message.reply_to_message.text

            topic = Topic(chat_id=message.chat_id, text=text, subtopics = [])
            topic.save()
            self.set_topic(topic)

    def on_topic_set(self, chat_id, topic, topic_text):
        self.adapter.bot.sendMessage(chat_id=chat_id, text="⚠ Should set the topic to {}".format(topic_text))
        pass

    def on_subtopic_pop(self, chat_id, topic):
        self.adapter.bot.sendMessage(chat_id=chat_id, text="⚠ Should pop the subtopic off the end")
        pass

    def on_subtopic_push(self, chat_id, topic, subtopic_text):
        self.adapter.bot.sendMessage(chat_id=chat_id, text="⚠ Should push a subtopic onto the end with text {}".format(subtopic_text))
        pass

    def on_subtopic_shift(self, chat_id, topic):
        self.adapter.bot.sendMessage(chat_id=chat_id, text="⚠ Should shift the subtopic from the beginning")
        pass

    def on_subtopic_unshift(self, chat_id, topic, subtopic_text):
        self.adapter.bot.sendMessage(chat_id=chat_id, text="⚠ Should prepend a subtopic to the beginning with text {}".format(subtopic_text))
        pass

    def on_subtopic_pop_all(self, chat_id, topic):
        self.adapter.bot.sendMessage(chat_id=chat_id, text="⚠ Should remove all subtopics")
        pass

    def on_topic_command(self, update, *args, **kwargs):
        message = get_message(update)
        chat_id = message.chat_id

        set = kwargs.get('set', False)
        pop = kwargs.get('pop', False)
        push = kwargs.get('push', False)
        unshift = kwargs.get('unshift', False)
        shift = kwargs.get('shift', False)
        fix = kwargs.get('fix', False)

        topic = TopicPlugin.get_topic(chat_id)

        if topic is None and init is False:
            self.initialize_topic(chat_id, topic, message)

        if fix:
            self.set_topic(topic)
            return

        if set:
            if not bool(message.reply_to_message):
                message.reply_text(chat_id=chat_id, text="❌ Use --set when replying.")
                return
            topic_text = message.reply_to_message.text
            if bool(topic_text):
                message.reply_text(chat_id=chat_id, text="❌ Use --set replying to a text message.")
                return
            self.on_topic_set(chat_id, topic, topic_text)

        elif shift:
            self.on_subtopic_shift(chat_id, topic)

        elif unshift:
            if not bool(message.reply_to_message):
                message.reply_text(chat_id=chat_id, text="❌ Use --unshift when replying.")
                return
            subtopic_text = message.reply_to_message.text
            if bool(subtopic_text):
                message.reply_text(chat_id=chat_id, text="❌ Use --unshift replying to a text message.")
                return
            self.on_subtopic_unshift(chat_id, topic, subtopic_text)

        elif pop:
            self.on_subtopic_pop(chat_id, topic)

        elif push:
            if not bool(message.reply_to_message):
                message.reply_text(chat_id=chat_id, text="❌ Use --push when replying.")
                return
            subtopic_text = message.reply_to_message.text
            if bool(subtopic_text):
                message.reply_text(chat_id=chat_id, text="❌ Use --push replying to a text message.")
                return
            self.on_subtopic_push(chat_id, topic, subtopic_text)
