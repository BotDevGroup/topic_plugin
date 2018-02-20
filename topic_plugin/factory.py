from telegram import InlineKeyboardMarkup, InlineKeyboardButton

class TopicPluginFactory:

    def __init__(self, name):
        self.name = name


    def createKeyboard(self, rows):
        buttons = list(map(lambda row: self.createRow(row), rows))
        return InlineKeyboardMarkup(buttons)

    def createRow(self, cells):
        return list(map(lambda cell: self.createButton(**cell), cells))

    def createButton(self, label, action, data):
        callback_data = self.prepareCallbackData(action, data)
        return InlineKeyboardButton(text=label, callback_data=callback_data)

    def prepareCallbackData(self, action, data):
        return "{name}:{action}:{data}".format(name=self.name, action=action, data=data)

