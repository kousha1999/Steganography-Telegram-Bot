from telegram.ext import Updater, MessageHandler, CommandHandler, Filters, RegexHandler, ConversationHandler
from telegram import ReplyKeyboardMarkup, ReplyKeyboardRemove
import logging, emoji, pyaes, stepic, binascii
from PIL import Image

REQUEST_KWARGS={
    #set proxy (here we used tor as default)
    'proxy_url': 'socks5://localhost:9050',
    'urllib3_proxy_kwargs': {
        'username': '',
        'password': '',
    }
}
# Enable logging
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)
PHOTO, PTEXT, PKEY = range(3)
PHOTO2,PKEY2 = range(2)

bot_token ='Your Telegram Bot token must paste here'
# updater = Updater(token=bot_token) # it doesn't use proxy
updater = Updater(token=bot_token, request_kwargs=REQUEST_KWARGS) #it use proxy
dispatcher = updater.dispatcher

def encoding(bot, update):
    update.message.reply_text('First, Send the photo as simple picture to start encoding.')
    logger.info('Send photo session')
    return PHOTO


def photo(bot, update):
    global ci
    user = update.message.from_user
    ci = str(update.message.chat_id)
    photo_file = bot.get_file(update.message.photo[-1].file_id)
    photo_file.download('{}.jpg'.format(str(update.message.chat_id)))
    logger.info("Photo of %s: %s", user.first_name, 'debug.jpg')
    update.message.reply_text('Well. tell me plain text!')

    return PTEXT

def ptext(bot, update):
    global encode_text
    user = update.message.from_user
    logger.info("plain text of %s: %s", user.first_name, update.message.text)
    encode_text = update.message.text
    update.message.reply_text('Send your key!\n(AES key must be either 16 or 32 character)')
    return PKEY

def pkey(bot, update):
    global encode_key
    user = update.message.from_user
    logger.info('key of %s: %s', user.first_name, update.message.text)
    encode_key = update.message.text
    update.message.reply_text("Nice...\nYour image will send in a few moment\nSteps:\n1) Download Image\n2) Click on 3dots in the top-right corner and choose 'Save to downloads'\nYou can Decrypt with /decode command.")
    stegano_encode(encode_text, encode_key, ci)
    bot.send_document(update.message.chat_id, document=open('{}_e.png'.format(str(update.message.chat_id)), 'rb'), timeout=1000)
    return ConversationHandler.END

def stegano_encode(encode_text, encode_key, ci):
    # A 256 bit (32 byte) key
    key = encode_key
    #Get The plainText
    plaintext = encode_text
    # key must be bytes, so we convert it
    key = key.encode('utf-8')
    #Encrypt the key & plain Text
    aes = pyaes.AESModeOfOperationCTR(key)
    ciphertext = aes.encrypt(plaintext)
    #Turn the cipher text to binary
    binary_value = binascii.b2a_base64(ciphertext)
    #putting the Binary value inside the image and create the stegano image
    img = Image.open("{}.jpg".format(ci))
    aa = stepic.encode(img, binary_value)
    aa.save("{}_e.png".format(ci))

def decoding(bot, update):
    update.message.reply_text('Send photo as file')
    logger.info('send photo session')
    return PHOTO2

def photo2(bot, update):
    user = update.message.from_user
    new_file = bot.get_file(update.message.document.file_id, timeout = 1000)
    new_file.download('{}_d.png'.format(str(update.message.chat_id)))
    logger.info("photo of %s: %s",user.first_name,'image.png')
    update.message.reply_text('Send me your key')

    return PKEY2

def pkey2(bot, update):
    global decode_key
    user = update.message.from_user
    logger.info('key of %s: %s', user.first_name, update.message.text)
    decode_key = update.message.text
    decode_key = decode_key.encode('utf-8')
    stegano_decode(decode_key, update.message.chat_id)
    update.message.reply_text(str(decrypted))
    return ConversationHandler.END


def stegano_decode(decode_key, ci):
    global decrypted
    #open the fake image and start the decrypting
    new_img = Image.open("{}_d.png".format(ci))
    data_decode = stepic.decode(new_img).rstrip('\n')
    #turning data out form ascci
    encrypted = binascii.a2b_base64(data_decode)
    # DECRYPTION
    # CRT mode decryption requires a new instance be created
    aes = pyaes.AESModeOfOperationCTR(decode_key)
    # decrypted data is always binary, need to decode to plaintext
    decrypted = aes.decrypt(encrypted).decode('utf-8')


def cancel(bot, update):
    user = update.message.from_user
    logger.info("User %s canceled the conversation.", user.first_name)
    update.message.reply_text('Bye! I hope we can talk again some day.')
    return ConversationHandler.END

def Help(bot, update):
    bot.sendMessage(update.message.chat_id, text = "To use this bot use the /encode command to start encrypting and use the /decode command to start the decrypting")


def Start(bot, update):
    user = update.message.from_user
    update.message.reply_text(emoji.emojize("Hi "+user.first_name+" :heart_eyes_cat:\nWelcome To SteganoGraphy Bot :rose:\n:cl: List of Commands:\n----------------\n:one: Encode an image: /encode\n:two: Decode an image: /decode\n:three: And you can cancel task with /cancel anytime", use_aliases=True))


updater.dispatcher.add_handler(CommandHandler('start', Start))
updater.dispatcher.add_handler(CommandHandler('help', Help))

conv_handler = ConversationHandler(
    entry_points = [CommandHandler('encode', encoding)],

    states = {
        PHOTO: [MessageHandler(Filters.photo, photo)],
        PTEXT: [MessageHandler(Filters.text, ptext)],
        PKEY: [MessageHandler(Filters.text, pkey)]

    },
    fallbacks = [CommandHandler('cancel', cancel)]
)

conv_handler_decode = ConversationHandler(
    entry_points = [CommandHandler('decode',decoding)],

    states = {
        PHOTO2: [MessageHandler(Filters.document, photo2)],
        PKEY2:  [MessageHandler(Filters.text, pkey2)]
    },
    fallbacks = [CommandHandler('cancel',cancel)]
)
dispatcher.add_handler(conv_handler)
dispatcher.add_handler(conv_handler_decode)

#start bot..
updater.start_polling()
print("bot is running!")
updater.idle()
updater.stop()
