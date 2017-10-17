import mongoengine
from marvinbot.utils import localized_date

class Subtopic(mongoengine.Document):
    chat_id = mongoengine.LongField(required=True)

    text = mongoengine.StringField(required=True)

    user_id = mongoengine.LongField(required=True)
    username = mongoengine.StringField()

    date_added = mongoengine.DateTimeField(default=localized_date)
    date_modified = mongoengine.DateTimeField(default=localized_date)
    date_deleted = mongoengine.DateTimeField(required=False, null=True)

    def __repr__(self):
        return self.text

    def __str__(self):
        return self.__repr__()

class Topic(mongoengine.Document):
    id = mongoengine.SequenceField(primary_key=True)

    chat_id = mongoengine.LongField(required=True, unique=True)

    text = mongoengine.StringField(required=True)

    subtopics = mongoengine.ListField(mongoengine.ReferenceField(Subtopic, reverse_delete_rule=mongoengine.PULL))

    separator = mongoengine.StringField(default=' | ')

    user_id = mongoengine.LongField(required=True)
    username = mongoengine.StringField()

    date_added = mongoengine.DateTimeField(default=localized_date)
    date_modified = mongoengine.DateTimeField(default=localized_date)
    date_deleted = mongoengine.DateTimeField(required=False, null=True)

    @classmethod
    def by_id(cls, id):
        try:
            return cls.objects.get(id=id)
        except cls.DoesNotExist:
            return None

    @classmethod
    def by_chat_id(cls, chat_id):
        try:
            return cls.objects.get(chat_id=chat_id)
        except cls.DoesNotExist:
            return None

    def __repr__(self):
        return self.text if len(self.subtopics) == 0 else '{}{}{}'.format(self.text, self.separator, self.separator.join(subtopic.text for subtopic in self.subtopics))

    def __str__(self):
        return self.__repr__()