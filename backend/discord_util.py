#strings

DAVINCI_TOKEN = 'MTA5MTc2Mzg4NzQ1MzUwNzcwNA.GspQDe.qnWTlStz8jtf3Y9v-HtWRi6zCcfjAQ1gJHsxTE' #[Token of Discord bot]

SERVER_ID = '1091783093465128980' # [Server id here]

SALAI_TOKEN = 'OTAyNDY5MzcyNTYyNTM0NDEw.GzQhLp.PCerC9nXcbBlMktavcTXRhDLtYO4H5mBKtNTOg' #[Token of the Account from which you paid MidJourney ]

CHANNEL_ID = '1091783093465128983' #[Channel in which commands are sent]

#boolean
USE_MESSAGED_CHANNEL = False

#don't edit the following variable
MID_JOURNEY_ID = "936929561302675456"  #midjourney bot id
targetID       = ""
targetHash     = ""


import requests

def PassPromptToSelfBot(prompt : str):
    payload ={"type":2,"application_id":"936929561302675456","guild_id":SERVER_ID,
              "channel_id":CHANNEL_ID,"session_id":"2fb980f65e5c9a77c96ca01f2c242cf6",
              "data":{"version":"1077969938624553050","id":"938956540159881230","name":"imagine","type":1,"options":[{"type":3,"name":"prompt","value":prompt}],
                      "application_command":{"id":"938956540159881230",
                                             "application_id":"936929561302675456",
                                             "version":"1077969938624553050",
                                             "default_permission":True,
                                             "default_member_permissions":None,
                                             "type":1,"nsfw":False,"name":"imagine","description":"Create images with Midjourney",
                                             "dm_permission":True,
                                             "options":[{"type":3,"name":"prompt","description":"The prompt to imagine","required":True}]},
              "attachments":[]}}
    

    header = {
        'authorization' : SALAI_TOKEN
    }

    return requests.post("https://discord.com/api/v9/interactions", json = payload, headers = header)

