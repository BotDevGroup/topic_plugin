# -*- coding: utf-8 -*-
import logging

from telegram import Chat
from telegram.error import BadRequest

from marvinbot.handlers import CommandHandler, MessageHandler, CommonFilters, CallbackQueryHandler
from marvinbot.plugins import Plugin
from topic_plugin.factory import TopicPluginFactory
from topic_plugin.models import Topic, Subtopic

log = logging.getLogger(__name__)
MESSAGES_CACHE_KEY='topic-plugin-messages'

class TopicPlugin(Plugin):
    def __init__(self):
        super(TopicPlugin, self).__init__('topic_plugin')
        self.factory = None
        self.messages = {}

    def get_default_config(self):
        return {
            'short_name': self.name,
            'enabled': True
        }

    def configure(self, config):
        pass

    def setup_handlers(self, adapter):
        log.info("Setting up handlers for Topic plugin")
        self.add_handler(CommandHandler('topic', self.on_topic_command, command_description='Allows the user to control the topic on the chat title.'))
                         # .add_argument('--set', help='Set the topic', action='store_true')
                         # .add_argument('--unset', help='Unset the topic', action='store_true')
                         # .add_argument('--pop', help='Pop the subtopic off the end', action='store_true')
                         # .add_argument('--push', help='Push a subtopic onto the end', action='store_true')
                         # .add_argument('--shift', help='Shift the subtopic from the beginning', action='store_true')
                         # .add_argument('--unshift', help='Prepend a subtopic to the beginning', action='store_true')
                         # .add_argument('--fix', help='Fix chat title', action='store_true'))

        # Revert chat topic & subtopics if it is changed by someone else
        self.add_handler(MessageHandler([CommonFilters.status_update.new_chat_title], self.on_new_chat_title))
        # Delete Topic if bot leaves the chat
        self.add_handler(MessageHandler([CommonFilters.status_update.left_chat_member], self.on_left_chat_member))
        # Handle button presses
        self.add_handler(CallbackQueryHandler('{}:'.format(self.name), self.on_button), priority=1)
        # TODO: Update subtopic or topic if linked message is edited

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
            if topic:
                for subtopic in topic.subtopics:
                    subtopic.delete()
                topic.delete()

    def set_chat_title_from_topic(self, topic):
        try:
            self.adapter.bot.setChatTitle(chat_id=topic.chat_id, title=str(topic))
            return True
        except BadRequest as ex:
            self.adapter.bot.sendMessage(chat_id=topic.chat_id, text="❌ {}".format(ex))
            return False


    def initialize_topic(self, chat_id, current_text, text, user_id, username):
        same = current_text == text

        # try:
        topic = Topic(chat_id=chat_id, text=text, subtopics=[], user_id=user_id, username=username)
        if same or self.set_chat_title_from_topic(topic):
            topic.save()
            return topic
        return None
        # except BadRequest as ex:
        #     self.adapter.bot.sendMessage(chat_id=chat_id, text="❌ {}".format(ex))
        #     return None

    def on_topic_set(self, **kwargs):
        topic = kwargs.get('topic')
        topic.text = kwargs.get('text')
        topic.user_id = kwargs.get('user_id')
        topic.username = kwargs.get('username')
        if self.set_chat_title_from_topic(topic):
            topic.save()
            return topic

    def on_topic_unset(self, **kwargs):
        topic = kwargs.get('topic')
        for subtopic in topic.subtopics:
            subtopic.delete()
        topic.delete()

    def on_subtopic_pop(self, **kwargs):
        topic = kwargs.get('topic')
        subtopic = topic.subtopics.pop()
        subtopic.delete()
        if self.set_chat_title_from_topic(topic):
            topic.save()

    def on_subtopic_push(self, **kwargs):
        topic = kwargs.get('topic')
        config = {
            "chat_id": kwargs.get('chat_id'),
            "text": kwargs.get('text'),
            "user_id": kwargs.get('user_id'),
            "username": kwargs.get('username')
        }
        subtopic = Subtopic(**config)

        topic.subtopics.append(subtopic)
        if self.set_chat_title_from_topic(topic):
            subtopic.save()
            topic.save(cascade=True)

    def on_subtopic_shift(self, **kwargs):
        topic = kwargs.get('topic')
        subtopic = topic.subtopics.pop(0)
        if self.set_chat_title_from_topic(topic):
            topic.save()
            subtopic.delete()

    def on_subtopic_remove(self, **kwargs):
        topic = kwargs.get('topic')
        index = int(kwargs.get('message_id'))
        subtopic = topic.subtopics.pop(index)
        if self.set_chat_title_from_topic(topic):
            topic.save()
            subtopic.delete()

    def on_subtopic_unshift(self, **kwargs):
        topic = kwargs.get('topic')
        config = {
            "chat_id": kwargs.get('chat_id'),
            "text": kwargs.get('text'),
            "user_id": kwargs.get('user_id'),
            "username": kwargs.get('username')
        }
        subtopic = Subtopic(**config)

        topic.subtopics = [subtopic] + topic.subtopics
        if self.set_chat_title_from_topic(topic):
            subtopic.save()
            topic.save(cascade=True)

    def can_user_change_info(self, message, user_id):
        member = message.chat.get_member(user_id=user_id)
        return message.chat.all_members_are_administrators \
                 or member.status == 'creator' \
                 or (member.status == 'administrator' and member.can_change_info)

    def on_button(self, update):
        query = update.callback_query
        button_message = query.message
        name, action, message_id = query.data.split(":")
        message_id = int(message_id)
        message_text = self.messages.get(message_id, None)

        chat_id = button_message.chat.id
        user_id = button_message.from_user.id
        username = button_message.from_user.username
        if not self.can_user_change_info(button_message, user_id):
            query.answer(text='❌ You are not allowed to do that.')
            return

        topic = TopicPlugin.get_topic(button_message.chat.id)
        has_topic = bool(topic)

        if not has_topic:
            if action != 'init':
                return
            current_text = button_message.chat.title
            self.initialize_topic(chat_id, current_text, message_text, user_id, username)
            button_message.edit_text(text='📋 The title of this chat is now controlled using /topic.')
            return

        action_args = {
            'chat_id': chat_id,
            'topic': topic,
            'text': message_text,
            'user_id': user_id,
            'username': username,
            'message_id': message_id
        }

        actions = {
            'set': self.on_topic_set,
            'shift': self.on_subtopic_shift,
            'unshift': self.on_subtopic_unshift,
            'pop': self.on_subtopic_pop,
            'push': self.on_subtopic_push,
            'unset': self.on_topic_unset,
            'remove': self.on_subtopic_remove,
        }

        action = actions[action]
        if not action:
            return

        action(**action_args)

        # message = update.effective_messsage
        # log.info(query)
        # query.answer(text='Done.', show_alert=True)
        query.answer(text='Done.')
        # message.edit_text(
        # message.reply_text(text=str(query))
        #message.edit_reply_markup(reply_markup=None)
        button_message.delete()

    def get_topic_pretty(self, topic):
        result = 'Current topic: {}\n\n'.format(topic.text)
        i = 1
        if len(topic.subtopics):
            result += 'Subtopics:\n' + '\n'.join(
                ['#{}: {}'.format(index, subtopic.text) for index,subtopic in enumerate(topic.subtopics, start=1)]
            )
        return result

    def on_topic_command(self, update, *args, **kwargs):
        message = update.effective_message

        if message.chat.type == Chat.PRIVATE:
            message.reply_text(text="❌ You cannot use this command in private chats.")
            return

        user_id = update.effective_user.id
        if not self.can_user_change_info(message, user_id):
            message.reply_text(text="❌ You are not allowed to do that.")
            return

        chat_id = update.effective_chat.id
        message_id = message.message_id

        is_replying = bool(message.reply_to_message) and bool(message.reply_to_message.text)
        if is_replying:
            self.messages[message_id] = message.reply_to_message.text

        topic = TopicPlugin.get_topic(chat_id)
        has_topic = bool(topic)

        factory = TopicPluginFactory(self.name)

        prompt = self.get_topic_pretty(topic) + '\n\nChoose an action:'

        if not has_topic:
            if not is_replying:
                message.reply_text(text="❌ You need to set a topic first.")

            else:
                reply_markup = factory.createKeyboard([
                    [
                        {
                            'label': '✅ Set as topic',
                            'action': 'init',
                            'data': message_id
                        }
                    ]
                ])
                message.reply_text(text=prompt, reply_markup=reply_markup)
        else:
            if is_replying:
                reply_markup = factory.createKeyboard([
                    [

                        {
                            'label': '⬅ Add first',
                            'action': 'unshift',
                            'data': message_id
                        },
                        {
                            'label': '➡ Add last',
                            'action': 'push',
                            'data': message_id
                        }
                    ],
                    [
                        {
                            'label': '✅ Set as title',
                            'action': 'set',
                            'data': message_id
                        }
                    ]
                ])
                message.reply_text(text=prompt, reply_markup=reply_markup)
            else:
                if len(topic.subtopics) > 0:
                    remove_buttons = [
                        {
                            'label': '🗑 Remove #{}'.format(index+1),
                            'action': 'remove',
                            'data': index
                        } for index,subtopic in enumerate(topic.subtopics)
                    ]
                    reply_markup = factory.createKeyboard([
                        remove_buttons,
                        [
                            {
                                'label': '🚫 Disable topic management',
                                'action': 'unset',
                                'data': message_id
                            }
                        ]
                    ])
                else:
                    reply_markup = factory.createKeyboard([
                        [
                            {
                                'label': '🚫 Disable topic management',
                                'action': 'unset',
                                'data': message_id
                            }
                        ]
                    ])
                message.reply_text(text=prompt, reply_markup=reply_markup)

        # if not topic and not set:
        #     message.reply_text(text="❌ You need to set a topic first.")
        #     return
        #
        # if fix:
        #     self.set_chat_title_from_topic(topic)
        #     return
        #
        # if set:
        #     if not topic:
        #         topic = self.initialize_topic(chat_id, topic, message, user_id, username)
        #
        #     if not message.reply_to_message or not message.reply_to_message.text:
        #         message.reply_text(text="❌ Use --set when replying to a message containing text.")
        #         return
        #
        #     topic_text = message.reply_to_message.text
        #     self.on_topic_set(chat_id, topic, topic_text, user_id, username)
        #
        # elif unset:
        #     topic.delete()
        #     message.reply_text(text="❌ Topic has been unset.")
        #
        # elif shift:
        #     if len(topic.subtopics) == 0:
        #         message.reply_text(text="❌ There are no subtopics to shift off.")
        #         return
        #     self.on_subtopic_shift(chat_id, topic)
        #
        # elif unshift:
        #     if not message.reply_to_message or not message.reply_to_message.text:
        #         message.reply_text(text="❌ Use --unshift when replying to a message containing text.")
        #         return
        #
        #     # TODO: Check if there's not a subtopic with this text
        #     subtopic_text = message.reply_to_message.text
        #     self.on_subtopic_unshift(chat_id, topic, subtopic_text, user_id, username)
        #
        # elif pop:
        #     if len(topic.subtopics) == 0:
        #         message.reply_text(text="❌ There are no subtopics to pop off.")
        #         return
        #     self.on_subtopic_pop(chat_id, topic)
        #
        # elif push:
        #     if not message.reply_to_message or not message.reply_to_message.text:
        #         message.reply_text(text="❌ Use --push when replying to a message containing text.")
        #         return
        #
        #     # TODO: Check if there's not a subtopic with this text
        #     subtopic_text = message.reply_to_message.text
        #     self.on_subtopic_push(chat_id, topic, subtopic_text, user_id, username)
