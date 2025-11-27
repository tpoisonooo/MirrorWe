from dotenv import load_dotenv

load_dotenv()

class WeChatAPI:
    def __init__(self):
        self.license_path = get_env_or_raise('WKTEAM_LICENSE')
        if os.path.exists(self.license_path):
            with open(self.license_path) as f:
                jsonobj = json.load(f)
                self.auth = jsonobj['auth']
                self.wId = jsonobj['wId']
                self.wcId = jsonobj['wcId']
                self.qrCodeUrl = jsonobj['qrCodeUrl']
                logger.debug(jsonobj)
    
    