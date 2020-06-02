#Googleapis
import pickle
from googleapiclient.discovery import build

#GApi message decoding
import base64
#from apiclient import errors

#VKApi import
import vk_api
# from vk_api.bot_longpoll import VkBotLongPoll, VkBotEventType

#other
import time
import os

def main():

    peer_destination_id = 2000000003
    sleep_time = 180
    timehrs = 3

    timehrs = timehrs * 3600
    print("Searching google api token...") #GMail authorisation
    creds = None
    if os.path.exists('token_PI110.pickle'):
        with open('token_PI110.pickle', 'rb') as token:
            creds = pickle.load(token)
        print("Success")
    else:
        print("No token found. Please generate another with Gen.py.\nTerminating...")
        exit()

    print("Connecting to GoogleAPI...")
    service = None
    for i in range(10):
        try:
            print("Trying... ", end='')
            service = build('gmail', 'v1', credentials=creds)
            break
        except:
            print("fail")
            continue
    if service == None:
        print("Failed to connect to GoogleAPI. Terminating...")
        exit()
    else:
        print("success")

    # VK authorisation
    print("Searching for vkapi.token...")
    token = ""
    if os.path.exists('vkapi.token'):
        with open('vkapi.token', 'r') as f:
            token = f.readline()
            if token[-1]=='\n':
                token = token[:-1]
    else:
        print("vkapi.token not found. Terminating...")
        exit()
    print("Connecting to VKApi...")
    try:
        vk = vk_api.VkApi(token=token)
        vk_upload = vk_api.upload.VkUpload(vk)
        print("Success")
    except:
        print("Failed to connect to VKApi. Check your token. \nTerminating...")
        exit()

    if not os.path.exists('Attach_dir') or os.path.isfile('Attach_dir'):
        print("Creating attachment dir...")
        os.system("mkdir Attach_dir")

    last_id = ""
    last_time = -1
    if os.path.exists("Last_MSG"):
        with open('Last_MSG', 'r') as f:
            last_id = f.readline()[:-1]
            last_time = int(f.readline())
    else:
        print("No Last_MSG found. Generating...")
        messages_list = GmailListMessages(service)
        if not str(messages_list) == "Error":
            with open('Last_MSG', 'w') as f:
                last_id = messages_list[0]['id']
                last_time = int(GmailGetMessage(service, last_id)['internalDate'])
                f.write("%s\n%d" % (last_id, last_time))
        else:
            print("Failed to generate Last_MSG. \nTerminating...")
            exit()

    # Main endless cycle
    while True:
        messages_list = GmailListMessages(service)
        if str(messages_list) == 'Error':
            print("%s : Failed to get messages list" % time.strftime("%d-%m %H:%M:%S", time.gmtime(time.time() + timehrs)))
            time.sleep(60)
            continue

        if messages_list[0]['id'] != last_id:
            print("Case found")
            print("Parsing by ID...")
            message_count_id = ParseMessagesByID(messages_list, last_id, 10)
            if message_count_id == -1:
                print("Something went wrong, probably, message was deleted\nParsing by time...")
                message_count_id = ParseMessagesByTime(service, messages_list, last_time, 10)
                if message_count_id == -1:
                    print("Parsing went wrong. Pointing to last message...")
                    last_id = messages_list[0]['id']
                    last_time = int(GmailGetMessage(service, last_id)['internalDate'])
                    with open('Last_MSG', 'w') as f:
                        f.write("%s\n%d" % (last_id, last_time))
                    print("%s : id\'s got fixed. Going to sleep..." % time.strftime("%d-%m %H:%M:%S", time.gmtime(time.time() + timehrs)))
                    time.sleep(sleep_time)
                    continue

            # Found id from unread to last
            for i in range(message_count_id, -1, -1):
                attach_names = ""
                current_message = GmailGetMessage(service, messages_list[i]['id'])
                if 'parts' in current_message['payload']:
                    print("Probably have attachments...")
                    os.system("rm -rf ./Attach_dir/*") # Cleaning up needed dir
                    attach_list = GmailGetAttachments(service, current_message['payload']['parts'], messages_list[i]['id'])
                    for filename in attach_list:
                        if attach_names != "":
                            attach_names += ","
                        attach_names += VkUploadAttachment(vk_upload, filename, peer_destination_id)

                    if 'parts' in current_message['payload']['parts'][0]:
                        encrypted_body = current_message['payload']['parts'][0]['parts'][0]['body']['data']
                    else:
                        encrypted_body = current_message['payload']['parts'][0]['body']['data']
                else:
                    encrypted_body = current_message['payload']['body']['data']
                decrypted_body = base64.urlsafe_b64decode(encrypted_body).decode('utf-8')
                output_message = ParseMessageCreds(current_message['payload']['headers'])
                print(output_message)
                if decrypted_body[:9].upper() == "<!DOCTYPE":
                    output_message += "<Unknown HTML-based message>"
                else:
                    output_message += decrypted_body
                if len(output_message) > 4096:
                    output_message = output_message[:4092]+"..."

                print(attach_names)
                vk.method('messages.send', {'peer_id': peer_destination_id, 'random_id': int(round(time.time() * 1000)), 'message': output_message[:4095], 'attachment':attach_names})
                last_id = messages_list[i]['id']
                last_time = int(GmailGetMessage(service, last_id)['internalDate'])
                with open('Last_MSG', 'w') as f:
                    f.write("%s\n%d" % (last_id, last_time))
            os.system("rm -rf ./Attach_dir/*")

        print('%s : Done. Going to sleep...' % time.strftime("%d-%m %H:%M:%S", time.gmtime(time.time() + timehrs)))
        time.sleep(sleep_time)

# **********************************************************************************************************

def GmailListMessages(service):
    try:
        response = service.users().messages().list(userId="me", labelIds=['INBOX']).execute()
        messages = []
        if 'messages' in response:
            messages.extend(response['messages'])
            return messages
    except:
        print("[GmailListMessages] Unintended error...")
        return 'Error'

def GmailGetMessage(service, msg_id):
    try:
        message = service.users().messages().get(userId="me", id=msg_id).execute()
        return message
    except:
        print("[GmailGetMessage] Unintended error...")
        return 'Error'

def ParseMessagesByID(messages_list, last_id, messages_amount=5):
    i=1
    while i<messages_amount:
        if messages_list[i]['id'] == last_id:
            return i-1
        i+=1
    if i==messages_amount:
        return -1

def ParseMessagesByTime(service, messages_list, last_time, messages_amount=5):
    i=0
    while i<messages_amount:
        current_message = GmailGetMessage(service, messages_list[i]['id'])
        if int(current_message['internalDate']) < last_time:
            return i-1
        i+=1
    if i==messages_amount:
        return -1

def GmailGetAttachments(service, message, msg_id, store_dir="Attach_dir/"):
    attachments = []
    for part in message:
        if part['filename']:
            attach = service.users().messages().attachments().get(userId="me", messageId=msg_id, id=part['body']['attachmentId']).execute()
            file_data = base64.urlsafe_b64decode(attach['data'].encode('UTF-8'))
            attachments.append(part['filename'])
            path = ''.join([store_dir, part['filename']])
            with open(path, 'wb') as f:
                f.write(file_data)
    return attachments


def ParseMessageCreds(message_headers):
    output = ""
    for i in message_headers:
        if i['name'] == 'From':
            output = "New message from " + i['value']+"\n"
            break
    for i in message_headers:
        if i['name'] == 'Date':
            output += "[ " + str(i['value'])[:-6]+" ]\n"
            break
    for i in message_headers:
        if i['name'] == 'Subject':
            output += "Subject: " + i['value'] + "\n\n"
            break
    return output


def VkUploadAttachment(vk_upload, document_name, peer_destination_id):
    path = ''.join(['Attach_dir/', document_name])
    with open(path, 'rb') as f:
        sent_doc = vk_upload.document_message(doc=f, title=document_name, peer_id=peer_destination_id)
    return sent_doc['doc']['url'][15:61]

if __name__ == '__main__':
    main()
