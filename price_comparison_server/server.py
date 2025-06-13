import requests
import gzip
import xml.etree.ElementTree as ET
import sqlite3
from io import BytesIO
from bs4 import BeautifulSoup
import schedule
import time
import os
from datetime import datetime
from typing import List, Dict, Any
import logging

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Import database models and connection
from database.connection import get_db
from database.models import Store, Price

def get_store_city(snif_key):
    chain_id = snif_key.split('-')[0]
    sub_chain_id = snif_key.split('-')[1]
    store_id = snif_key.split('-')[2]
    
    store_cities = {
    "7290027600007": {  # Shufersal
        "001": "Tel Aviv",  # שלי ת"א- בן יהודה
        "002": "Jerusalem",  # שלי ירושלים- אגרון
        "003": "Givatayim",  # שלי גבעתיים- סירקין
        "004": "Haifa",  # שלי חיפה- כרמל
        "005": "Jerusalem",  # שלי ירושלים- יובל
        "007": "Tel Aviv",  # שלי ת"א- ארלוזורוב
        "009": "Netanya",  # שלי נתניה- ויצמן
        "011": "Tel Aviv",  # שלי ת"א- נורדאו
        "012": "Bnei Brak",  # יש בני ברק- ירושלים
        "013": "Beit Shemesh",  # דיל בית שמש- העליה
        "014": "Ashkelon",  # דיל ברנע אשקלון
        "015": "Petah Tikva",  # יש פ"ת- רוטשילד
        "017": "Haifa",  # שלי חיפה- חורב
        "018": "Holon",  # דיל חולון-קרן היסוד
        "019": "Haifa",  # שלי חיפה- זיו
        "020": "Rehovot",  # שלי רחובות- הרצל
        "021": "Jerusalem",  # יש מרים ירושלים- פארן
        "022": "Netanya",  # שלי נתניה- סמילנסקי
        "023": "Metar",  # שלי מיתר
        "024": "Ashdod",  # שלי אשדוד- הנביאים
        "025": "Kfar Saba",  # אקספרס ארבל כ"ס
        "026": "Givatayim",  # BE בלוך גבעתיים
        "027": "Raanana",  # שלי רעננה- אחוזה
        "028": "Tel Aviv",  # שלי ת"א- צה"ל
        "029": "Harish",  # אקספרס האודם חריש
        "030": "Ramat Gan",  # שלי רמת גן- קריניצי
        "032": "Ramat Gan",  # שלי רמת גן- קסם
        "033": "Haifa",  # שלי חיפה- סטלה
        "034": "Ramat Hasharon",  # שלי רמת השרון- סוקולוב
        "035": "Beer Sheva",  # דיל אקסטרה באר-שבע ולפסו
        "036": "Kfar Saba",  # שלי כ"ס- רוטשילד
        "038": "Haifa",  # שלי חיפה- דניה
        "039": "Tel Aviv",  # שלי ת"א- ברזיל
        "040": "Beer Sheva",  # שלי ב"ש- עומר
        "041": "Tel Aviv",  # BE דיזנגוף סנטר
        "042": "Jerusalem",  # שלי ירושלים- ניות
        "043": "Hod Hasharon",  # שלי הוד השרון- הבנים
        "045": "Jerusalem",  # דיל ירושלים- תלפיות
        "049": "Beer Sheva",  # דיל ב"ש- הר בוקר
        "050": "Mevaseret Zion",  # שלי מבשרת ציון
        "051": "Herzliya",  # אקספרס הרצליה
        "056": "Harish",  # אקספרס חריש הרימון
        "057": "Ramat Hasharon",  # שלי רמת השרון- אוסישקין
        "061": "Tzur Moshe",  # אקספרס צור משה
        "062": "Rechasim",  # יש חסד רכסים
        "065": "Beer Sheva",  # דיל ב"ש- צ'ורלי
        "068": "Kiryat Motzkin",  # דיל כורדני
        "069": "Tel Aviv",  # שלי ת"א- רמת אביב ב
        "070": "Ramat Gan",  # שלי רמת גן- מרום נווה
        "071": "Nesher",  # דיל אקסטרה תל חנן נשר
        "072": "Reut",  # שלי רעות
        "073": "Ashdod",  # יש חסד אשדוד
        "076": "Ariel",  # דיל אריאל
        "077": "Harish",  # דיל חריש
        "078": "Jerusalem",  # יש הר נוף ירושלים-שאולזו
        "079": "Harish",  # אקספרס חריש
        "080": "Rishon LeZion",  # שלי ראשל"צ- נווה הדרים
        "081": "Modiin Illit",  # יש חסד מודיעין עלית דרום
        "082": "Holon",  # אקספרס חולון
        "083": "Beer Sheva",  # דיל ב"ש- שאול המלך
        "084": "Beit Hashmonai",  # אקספרס בית חשמונאי
        "087": "Raanana",  # דיל רעננה- החרושת
        "089": "Ramla",  # דיל עזריאלי - רמלה
        "090": "Beer Sheva",  # אקספרס גב ים באר שבע
        "091": "Emek Hefer",  # דיל עמק חפר- אזור תעשיה
        "092": "Ashdod",  # דיל אשדוד- שבט לוי
        "093": "Yehud",  # שלי יהוד- סביונים
        "095": "Hadera",  # דיל חדרה- קניון אורות
        "096": "Hadera",  # דיל חדרה- הפרדס
        "097": "Kiryat Shmona",  # דיל קרית שמונה- מתחם ביג
        "098": "Kiryat Tivon",  # דיל קרית טבעון- אלונים
        "101": "Hod Hasharon",  # שלי הוד השרון- ק מרגלית
        "102": "Pardesia",  # שלי פרדסיה- הנשיא
        "103": "Shoham",  # שלי שוהם- מרכז מסחרי
        "104": "Petah Tikva",  # שלי פ"ת- גד מכנס
        "105": "Petah Tikva",  # דיל פ"ת- אליעזר פרדימן
        "106": "Nes Ziona",  # דיל אקסטרה נס ציונה הפטי
        "109": "Rosh HaAyin",  # שלי ראש העין- ז'בוטינסקי
        "110": "Beer Sheva",  # דיל הפארק ב"ש
        "111": "Tiberias",  # יש חסד טבריה עלית-לב האג
        "113": "Rishon LeZion",  # דיל ראשל"צ- גולדה מאיר
        "114": "Jerusalem",  # דיל ירושלים- גילה
        "116": "Givatayim",  # שלי גבעתיים- מכתש
        "117": "Tel Aviv",  # שלי תל אביב-איכילוב
        "118": "Eilat",  # דיל אילת הסתת
        "119": "Modiin",  # דיל מודיעין- סנטר
        "121": "Nahariya",  # דיל נהריה- לוחמי הגטאות
        "122": "Yavne",  # דיל יבנה- ברוש דרך הים
        "123": "Holon",  # דיל חולון- גולדה
        "124": "Bat Yam",  # דיל בת ים- אורט ישראל
        "127": "Tirat Carmel",  # אקספרס טירת הכרמל
        "128": "Tirat Carmel",  # דיל טירת הכרמל- נחום חת
        "129": "Netanya",  # דיל אקסטרה נתניה- המלאכה
        "130": "Netanya",  # דיל נתניה- קלאוזנר עמליה
        "131": "Hod Hasharon",  # אקספרס הוד השרון
        "132": "Tel Aviv",  # דיל ת"א- השלום
        "133": "Beitar Illit",  # יש חסד ביתר עילית- הר"ן
        "134": "Modiin",  # דיל מודיעין- ישפרו סנטר
        "135": "Ashkelon",  # דיל אשקלון- פאור סנטר
        "139": "Safed",  # דיל צפת- דובק ויצמן
        "140": "Tel Hai",  # אקספרס תל חי
        "141": "Yokneam",  # דיל יוקנעם- שדרות רבין
        "142": "Zichron Yaakov",  # דיל זכרון- המייסדים
        "144": "Kfar Saba",  # דיל שבירו כפר סבא
        "145": "Netivot",  # BE נתיבות
        "147": "Zichron Yaakov",  # אקספרס זכרון
        "148": "Rehovot",  # אקספרס מלצר רחובות
        "150": "Tel Aviv",  # אקספרס רודנסקי ת"א
        "151": "Raanana",  # דיל רעננה- קניון רננים
        "152": "Arad",  # דיל ערד- ישפרו המנוף
        "153": "Ofakim",  # דיל אופקים- ז'בוטינסקי
        "155": "Tzur Yigal",  # דיל צור יגאל- מרכז מסחרי
        "159": "Haifa",  # דיל רמת הנשיא חיפה
        "163": "Sderot",  # דיל שדרות- הפלדה
        "164": "Ramat Gan",  # שלי רמת גן- ביאליק
        "166": "Ashdod",  # דיל אקסטרה אשדוד- הבושם
        "168": "Ashdod",  # שלי אשדוד- כינרת
        "169": "Beer Sheva",  # אקספרס באר שבע
        "171": "Tel Aviv",  # אקספרס אוסטשינסקי
        "173": "Kfar Yona",  # דיל כפר יונה
        "174": "Arad",  # דיל ערד- קניון
        "176": "Jerusalem",  # שערי רווחה ירושלים
        "177": "Mitzpe Ramon",  # דיל מצפה רמון- בן גוריון
        "178": "Petah Tikva",  # BE סגולה פתח תקווה
        "179": "Ramat Gan",  # שופרסל אקספרס הרוא"ה רמת גן
        "180": "Kiryat Motzkin",  # דיל ק.מוצקין- בן גוריון
        "181": "Ashkelon",  # דיל אשקלון- רמז
        "182": "Dimona",  # דיל דימונה- גולדה מאיר
        "184": "Rishon LeZion",  # דיל ראשל"צ- זבוטינסקי
        "186": "Haifa",  # אקספרס התשבי
        "187": "Maale Adumim",  # דיל קניון מעלה אדומים
        "188": "Yeruham",  # דיל ירוחם- צבי בורנשטיין
        "189": "Pardes Hana",  # דיל פרדס חנה
        "190": "Hatzor HaGlilit",  # דיל חצור- הגלילית
        "193": "Rishon LeZion",  # שלי ראשל"צ- מזרח
        "195": "Kiryat Bialik",  # דיל קריון- דרך עכו
        "199": "Bat Yam",  # דיל בת ים- בלפור
        "201": "Tel Aviv",  # BE בריגה
        "203": "Ramla",  # דיל רמלה לוד- הצופית
        "205": "Yehud",  # דיל יהוד- אלטלף
        "207": "Or Yehuda",  # יש אור יהודה - אליהו סעדו
        "208": "Eilat",  # דיל אילת נחל אורה
        "209": "Ashkelon",  # דיל אשקלון- רוטשילד
        "210": "Rishon LeZion",  # יוניברס ראשל"צ- שמוטקין
        "211": "Karmiel",  # דיל כרמיאל- אזור התעשיה
        "212": "Haifa",  # שלי חיפה- ורדיה
        "214": "Kiryat Ata",  # דיל קרית אתא- זבולון
        "215": "Kiryat Gat",  # דיל קרית גת- מלכי ישראל
        "216": "Kiryat Malachi",  # דיל קרית מלאכי- ז'בוטינסקי
        "217": "Migdal HaEmek",  # דיל מגדל העמק- שדרות שאול
        "218": "Nahariya",  # דיל נהריה- געתון
        "219": "Netanya",  # דיל נתניה- פולג
        "220": "Afula",  # דיל עפולה- שדרות יצחק רבין
        "221": "Petah Tikva",  # דיל פ"ת- יכין סנטר
        "222": "Kiryat Shmona",  # דיל קרית שמונה- תל חי
        "223": "Rishon LeZion",  # דיל ראשל"צ- רוטשילד
        "224": "Rehovot",  # דיל רחובות- קרית המדע
        "225": "Tel Aviv",  # דיל ת"א- רמת אביב
        "226": "Holon",  # דיל חולון- המרכבה
        "227": "Kiryat Ata",  # דיל-איקאה קרית אתא
        "228": "Binyamina",  # שלי בנימינה - הגביע
        "229": "Tel Aviv",  # דיל ת"א- יגאל אלון
        "230": "Kfar Saba",  # שלי כ"ס- ויצמן
        "231": "Raanana",  # אקספרס רעננה- רבקה גרובר
        "232": "Safed",  # שלי צפת- מ.מסחר רמת רזים
        "233": "Beer Sheva",  # BE באר שבע
        "234": "Jerusalem",  # יש חסד רסידו
        "236": "Eilat",  # אקספרס אילת שחמון
        "238": "Beer Yaakov",  # דיל באר יעקב
        "239": "Jaffa",  # אקספרס יפו- הדרור
        "240": "Rahat",  # דיל רהט
        "241": "Bnei Brak",  # דיל בני ברק איילון
        "242": "Hadera",  # BE ויוה חדרה
        "244": "Ramat Hasharon",  # דיל גלילות רמת השרון
        "245": "Jerusalem",  # דיל ירושלים- פסגת זאב
        "247": "Holon",  # שלי חולון- רבינוביץ
        "248": "Beer Sheva",  # דיל ב"ש- נווה מנחם
        "249": "Netanya",  # דיל נתניה- פולג
        "250": "Kiryat Ata",  # דיל קרית אתא- ברוך ברוך
        "251": "Afula",  # דיל עפולה- כורש
        "252": "Ein Shemer",  # BE עין שמר
        "254": "Kiryat Gat",  # דיל כרמי גת
        "255": "Kfar Tavor",  # דיל כפר תבור
        "256": "Nes Ziona",  # BE נס ציונה
        "259": "Kfar Saba",  # דיל גזית כ"ס- ויצמן
        "260": "Jerusalem",  # דיל ירושלים-קניון תלפיות
        "262": "Mazkeret Batya",  # שלי מזכרת בתיה- בגין
        "263": "Tel Aviv",  # שופרסל אקספרס מקס ברוד
        "265": "Holon",  # אקספרס חולון - זלמן ארן
        "266": "Eilat",  # שלי רזין אילת
        "267": "Katzrin",  # דיל קצרין- חרמון
        "269": "Petah Tikva",  # דיל אקסטרה פ"ת- סגולה
        "270": "Holon",  # BE חולון הפלד
        "271": "Rehovot",  # שלי רחובות- יעקובי
        "272": "Givatayim",  # שלי גבעתיים- ויצמן
        "274": "Tel Aviv",  # אקספרס ת"א- פלורנטין
        "276": "Rehovot",  # דיל אמט"ל רחובות
        "277": "Herzliya",  # אקספרס.בני בנימין הרצליה
        "278": "Petah Tikva",  # שלי פ"ת -העצמאות
        "279": "Tel Aviv",  # אקספרס-ת"א דרויאנוב
        "281": "Migdal HaEmek",  # דיל מגדל העמק- המדע
        "282": "Jerusalem",  # דיל צומת גבעת מרדכי
        "283": "Kiryat Ekron",  # דיל קרית עקרון- ביל"ו
        "284": "Tel Mond",  # שלי תל מונד- הדקל
        "285": "Petah Tikva",  # אקספרס סוקולוב פ"ת
        "287": "Givatayim",  # שלי גבעתיים-שביט
        "288": "Rehovot",  # יש רחובות- סירני
        "290": "Petah Tikva",  # דיל  פ"ת- יכין סנטר
        "295": "Bnei Brak",  # יש חסד בני ברק-שלמה המלך
        "296": "Petah Tikva",  # אקספרס פ"ת רחל המשוררת
        "297": "Hadera",  # יוניברס חדרה- ארבע האגודות
        "298": "Beer Sheva",  # BE אמות באר שבע
        "299": "Hod Hasharon",  # אקספרס הוד השרון
        "300": "Beerot Yitzhak",  # יש חסד בארות יצחק- פאוור
        "301": "Tel Aviv",  # אקספרס אחי מאיר
        "302": "Haifa",  # שלי חיפה- קלר
        "303": "Kiryat Tivon",  # אקספרס טבעון - יהודה הנשיא
        "305": "Tel Aviv",  # אקספרס ת"א- יהודה המכבי
        "306": "Haifa",  # יש נוה שאנן חיפה- חניתה
        "307": "Kiryat Ata",  # יש קרית אתא- זבולון
        "308": "Kiryat Ata",  # שלי קרית אתא- איינשטין
        "310": "Kiryat Haim",  # שלי קרית חיים- דגניה
        "311": "Rehovot",  # אקספרס רחובות- בוסתנאי
        "312": "Haifa",  # דיל חיפה- קרית אליעזר
        "313": "Kiryat Haim",  # שלי קרית חיים-אח"י אילת
        "314": "Haifa",  # יש חיפה- צרפת
        "315": "Kfar Netter",  # אקספרס כפר נטר
        "316": "Kiryat Motzkin",  # שלי קרית מוצקין-שד ויצמן
        "317": "Givat Ada",  # אקספרס גבעת עדה
        "318": "Holon",  # אקספרס חולון - וולפסון
        "319": "Akko",  # שלי עכו- שפירא
        "322": "Tel Aviv",  # גן העיר תל אביב
        "323": "Nof HaGalil",  # שלי רסקו נצרת עילית-הדקל
        "325": "Nes Ziona",  # אקספרס ששת הימים נס ציונ
        "326": "Nahariya",  # שלי נהריה- הגעתון
        "327": "Haifa",  # אקספרס חיפה- ראול ולנברג
        "329": "Yokneam",  # יש  יוקנעם עילית- היובלים
        "330": "Haifa",  # שלי חיפה- נתיב חן
        "331": "Tel Aviv",  # אקספרס ת"א- תוספתא
        "333": "Haifa",  # שלי חיפה- אורן
        "334": "Petah Tikva",  # אקספרס פ"ת - שפירא
        "335": "Kfar Saba",  # אקספרס כ"ס- בן גוריון
        "336": "Haifa",  # שלי חיפה- רמות ספיר
        "338": "Haifa",  # אקספרס כוכב הצפון
        "339": "Tiberias",  # דיל טבריה- העמקים
        "340": "Tel Aviv",  # אקספרס ת"א- זריצקי
        "341": "Ramat Gan",  # אקספרס רמת גן- הרוא"ה
        "342": "Karmiel",  # דיל כרמיאל- קניון לב
        "343": "Rosh HaAyin",  # שלי ראש העין- ברקן
        "344": "Maalot",  # דיל מעלות- דרך האלוף עוז
        "345": "Tel Aviv",  # BE מידטאון
        "347": "Gedera",  # אקספרס גדרה- דרך הפרחים
        "348": "Petah Tikva",  # אקספרס פ"ת- קק"ל
        "349": "Safed",  # יש חסד צפת- כנען
        "350": "Hadera",  # דיל גבעת אולגה-הרב ניסים
        "352": "Tayibe",  # Be טייבה
        "353": "Tel Aviv",  # אקספרס יותם
        "354": "Tel Aviv",  # אקספרס ת"א- קינג ג'ורג
        "357": "Tzoran-Kadima",  # שלי צורן קדימה- לב השרון
        "359": "Haifa",  # דיל חיפה- גרנד קניון
        "360": "Rishon LeZion",  # אקספרס מאירוביץ ראשל"צ
        "361": "Migdal HaEmek",  # דיל מגדל העמק- א ת דרומי
        "362": "Jerusalem",  # אקספרס קרן היסוד ירושלים
        "364": "Jerusalem",  # יש חסד בית וגן
        "365": "Pardes Hana",  # שלי פרדס חנה כרכור- קדמה
        "366": "Kfar Vradim",  # שלי כפרורדים- מרכז מסחר
        "368": "Nesher",  # אקספרס-נשר מרגנית
        "369": "Shoham",  # שלי שוהם- תרשיש
        "371": "Raanana",  # שלי ברניצקי
        "372": "Bat Yam",  # אקספרס בתים- חשמונאים
        "374": "Herzliya",  # שלי הרצליה- הבנים
        "375": "Kfar Saba",  # אקספרס כ"ס- הגליל
        "376": "Raanana",  # אקספרס רעננה- משה דיין
        "377": "Jerusalem",  # אקספרס ירושלים- הדסה
        "379": "Givatayim",  # אקספרס גבעתיים- כצנלסון
        "380": "Tel Aviv",  # אקספרס ת"א-מרמורק
        "382": "Petah Tikva",  # אקספרס פ"ת- היבנר
        "384": "Kiryat Bialik",  # אקספרס קרית ביאליק
        "385": "Tel Aviv",  # אקספרס מאיר יערי תל אביב
        "388": "Haifa",  # אקספרס דניה
        "390": "Petah Tikva",  # שופרסל אקספרס אם המושבות
        "391": "Elkana",  # אקספרס אלקנה
        "392": "Shilat",  # BE שילת
        "393": "Lehavim",  # אקספרס להבים באר שבע
        "394": "Kfar Saba",  # אקספרס הכרמל כפר סבא
        "396": "Netanya",  # דיל הקדר נתניה
        "397": "Afula",  # אקספרס פארק עפולה
        "398": "Netanya",  # אקספרס אגמים
        "400": "Rosh HaAyin",  # אקספרס שבזי ראש העין
        "413": "Online",  # שופרסל ONLINE
        "437": "Eilat",  # BE אייס מול אילת
        "444": "Beer Sheva",  # אקספרס.ב"ש אביסרור
        "445": "Rehovot",  # אקספרס רחובות
        "448": "Jerusalem",  # שערי רווחה
        "476": "Hod Hasharon",  # BE הוד השרון כיכר המושבה
        "477": "Modiin",  # אקספרס הציפורים מודיעין
        "478": "Gedera",  # אקספרס גדרה
        "479": "Ramat Gan",  # אקספרס בר אילן
        "482": "Ramla",  # BE רמלה נווה דורון
        "485": "Ashdod",  # BE אשדוד בלה
        "489": "Modiin",  # אקספרס מודיעין
        "496": "Jerusalem",  # יש חסד כנפי נשרים
        "499": "Afula Illit",  # יש חסד עפולה עילית
        "579": "Savyon",  # אקספרס סביון
        "593": "Beer Tuvia",  # יש חסד באר טוביה
        "595": "Bat Hefer",  # אקספרס בת חפר
        "596": "Tel Aviv",  # אקספרס אבן גבירול
        "598": "Tel Aviv",  # אקספרס הירדן
        "599": "Haifa",  # אקספרס ההסתדרות
        "600": "Tel Aviv",  # אקספרס ת"א- מגדל השרון
        "601": "Pardes Hana",  # BE פרדס חנה
        "602": "Ashkelon",  # BE אשקלון מרינה
        "606": "Beit Shemesh",  # יש חסד בית שמש
        "607": "Modiin Illit",  # יש חסד מודיעין עילית
        "608": "Jerusalem",  # יש חסד ירושלים-קרית שאול
        "609": "Elad",  # יש חסד אלעד
        "610": "Jerusalem",  # יש חסד ירושלים- רמת שלמה
        "611": "Bnei Brak",  # יש חסד בני ברק
        "613": "Nahariya",  # BE נהריה
        "614": "Netanya",  # BE נתניה
        "615": "Kfar Saba",  # BE כפר סבא
        "617": "Nazareth",  # BE נצרת
        "618": "Rishon LeZion",  # BE ראשון לציון
        "620": "Eilat",  # BE מלכת שבא אילת
        "621": "Netanya",  # BE סינמה סיטי נתניה
        "623": "Savyon",  # BE סביונים
        "631": "Holon",  # סניף וולפסון
        "633": "Nesher",  # BE נשר תל-חנן
        "634": "Bat Yam",  # BE בת ים
        "635": "Rosh Pina",  # BE ראש-פינה
        "637": "Raanana",  # BE רעננה
        "638": "Mishmar HaSharon",  # BE משמר השרון
        "639": "Ariel",  # BE אריאל
        "640": "Daliat al-Carmel",  # BE דלית אל כרמל
        "641": "Givatayim",  # BE גבעתיים
        "642": "Kiryat Tivon",  # BE אלונים- טבעון
        "643": "Petah Tikva",  # BE פתח תקוה
        "645": "Givat Shmuel",  # BE גבעת שמואל
        "648": "Kfar Saba",  # BE מאיר-כפר סבא
        "649": "Akko",  # BE עכו
        "650": "Haifa",  # BE חיפה
        "651": "Dror",  # BE דרורים
        "652": "Modiin",  # BE מודיעין
        "653": "Bnei Brak",  # BE בני-ברק
        "654": "Petah Tikva",  # BE אם המושבות
        "655": "Rehovot",  # BE רחובות מזרח
        "656": "Tel Aviv",  # סניף בן יהודה
        "658": "Kiryat Ata",  # BE קריית אתא
        "659": "Haifa",  # BE הדר
        "660": "Ramat Hasharon",  # סניף רמת השרון
        "662": "Ashdod",  # BE בית חולים אשדוד
        "664": "Jerusalem",  # BE בית חולים שערי צדק
        "665": "Hashmonaim",  # BE חשמונאים
        "666": "Modiin",  # BE עזריאלי מודיעין
        "667": "Hadera",  # BE מדיקל הלל יפה
        "668": "Netanya",  # BE קריית השרון
        "670": "Tel Aviv",  # BE איכילוב
        "672": "Ashdod",  # סניף אשדוד סיטי
        "673": "Haifa",  # BE פנורמה חיפה
        "674": "Tel Aviv",  # BE תל ברוך
        "675": "Sharon",  # BE שרונים
        "676": "Yokneam",  # BE יוקנעם
        "677": "Herzliya",  # BE הרצליה
        "678": "Afula",  # BE עפולה
        "679": "Karkur",  # BE כרכור מדיקל
        "681": "Shoham",  # BE שהם
        "682": "Kfar Saba",  # BE כפר סבא צפון
        "683": "Ashkelon",  # BE אשקלון דוידי
        "684": "Sderot",  # Be שדרות
        "685": "Tel Aviv",  # BE אזורי חן
        "688": "Petah Tikva",  # BE מדיקל-בלינסון
        "691": "Ashdod",  # Be אשדוד מדיקל
        "695": "Tel Aviv",  # BE אסותא רמת החייל
        "696": "Elad",  # BE מדיקל-אלעד
        "697": "Yarka",  # BE ירכא
        "698": "Karmiel",  # BE כרמיאל
        "712": "Hadera",  # BE עין הים חדרה
        "713": "Or Yam",  # BE אור ים
        "714": "Sakhnin",  # Be סכנין
        "715": "Agamim",  # BE אגמים
        "716": "Beer Sheva",  # Be mall 7 באר שבע
        "730": "Kadima",  # חנות עובדים מרכז שילוח
        "734": "Haifa",  # גוד מרקט גאולה
        "740": "Tel Aviv",  # אקספרס שלמה המלך
        "741": "Tel Aviv",  # אקספרס יצחק רבין
        "742": "Tel Aviv",  # אקספרס נווה אביבים
        "743": "Kiryat Gat",  # אקספרס קריית גת
        "748": "Eilat",  # BE שבעת הכוכבים
        "750": "Jerusalem",  # גוד מרקט שירת הים
        "752": "Kfar Saba",  # אקספרס דוכיפת
        "753": "Jerusalem",  # גוד מרקט רש"י
        "757": "Kiryat Ono",  # אקספרס קריית אונו
        "762": "Tel Aviv",  # BE אוסישקין
        "763": "Shfaram",  # BE שפרעם
        "764": "Ashdod",  # BE סטאר אשדוד
        "765": "Jerusalem",  # יש חסד בן איש חי
        "768": "Ramat Gan",  # אקספרס קרניצי
        "771": "Bnei Brak",  # גוד מרקט בני ברק
        "772": "Jerusalem",  # גוד מרקט מאה שערים
        "773": "Beit Shemesh",  # GOOD MARKET אהבת שלום
        "776": "Tira",  # BE טירה
        "777": "Tel Aviv",  # אקספרס נרקיסים
        "778": "Jerusalem",  # GOOD MARKET אהליאב
        "779": "Yavne",  # אקספרס יבנה
        "780": "Ramat Gan",  # אקספרס המעפיל
        "781": "Tel Aviv",  # BE פרישמן
        "782": "Rishon LeZion",  # BE ראשון לציון
        "783": "Modiin",  # BE מודיעין
        "784": "Petah Tikva",  # BE כפר גנים
        "785": "Maale Adumim",  # BE מעלה אדומים
        "786": "Kiryat Gat",  # BE כרמי גת
        "787": "Ariel",  # BE אריאל
        "788": "Efrat",  # BE אפרת
        "789": "Ofakim",  # גוד מרקט אופקים
        "790": "Ramla",  # דיל רמלה
        "842": "Tel Aviv",  # אקספרס מטודלה
        "843": "Beit Shemesh",  # גוד מרקט בית שמש
        "844": "Ramat Gan",  # אקספרס נגבה
        "845": "Kfar Saba",  # אקספרס נחשון
        "846": "Or Yam",  # אקספרס אור ים
        "854": "Givat Alonim"  # דיל גבעת אלונים
    },
        "7290696200003": {  # Victory
        "007": "Tel Aviv",  # מסעדת בריאה
        "052": "Ashkelon",  # אשקלון
        "001": "Gan Yavne",  # גן-יבנה
        "028": "Ganei Tikva",  # גני תקווה
        "075": "Tel Aviv",  # וייצמן
        "082": "Nes Ziona",  # סיטי נס ציונה
        "025": "Akko",  # עכו
        "059": "Afula",  # עפולה
        "070": "Tzur Yitzhak",  # צור יצחק
        "055": "Kiryat Gat",  # קרית גת
        "045": "Raanana",  # רעננה
        "061": "Tel Aviv",  # אוניברסיטה ת"א
        "047": "Ofakim",  # אופקים
        "005": "Oranit",  # אורנית
        "035": "Tel Aviv",  # אחד העם
        "097": "Online",  # אינטרנט
        "080": "Tel Aviv",  # אלנבי
        "030": "Elkana",  # אלקנה
        "008": "Ashdod",  # אשדוד
        "095": "Ashkelon",  # אשקלון בן גוריון
        "068": "Beer Sheva",  # באר שבע
        "073": "Beit Shean",  # בית שאן
        "014": "Beit Shemesh",  # בית שמש
        "041": "Ashkelon",  # ברנע
        "002": "Gedera",  # גדרה
        "065": "Tel Aviv",  # דיזנגוף
        "046": "Dimona",  # דימונה
        "009": "Tel Aviv",  # הארבעה
        "060": "Haifa",  # התנאים
        "022": "Hadera",  # חדרה
        "093": "Harish",  # חריש
        "086": "Tivon",  # טבעון
        "048": "Tirat Carmel",  # טירת הכרמל
        "056": "Yavne",  # יבנה
        "067": "Tel Aviv",  # יהודה הלוי
        "089": "Jerusalem",  # ירושלים מלחה
        "079": "Kfar Saba",  # כ"ס הירוקה
        "058": "Kfar Yona",  # כפר יונה
        "010": "Lod",  # לוד
        "077": "Lod",  # לוד נתב"ג
        "044": "Tel Aviv",  # לינקולן
        "038": "Mevaseret Zion",  # מבשרת
        "051": "Modiin",  # מודיעין
        "034": "Kiryat Motzkin",  # מוצקין
        "057": "Tel Aviv",  # מרגוזה
        "092": "Netivot",  # נתיבות
        "090": "Netanya",  # נתניה
        "016": "Tel Aviv",  # פלורנטין
        "087": "Tzemach",  # צמח
        "039": "Holon",  # קוגל
        "088": "Ramat Gan",  # קניון איילון
        "037": "Ashdod",  # קניון אשדוד
        "024": "Hadera",  # קניון לב חדרה
        "096": "Kiryat Ata",  # קריית אתא
        "054": "Kiryat Malachi",  # קרית מלאכי
        "026": "Rosh HaAyin",  # ראש העין
        "081": "Rosh HaAyin",  # ראש העין פארק אפק
        "071": "Rishon LeZion",  # ראשון לציון מזרח
        "023": "Rishon LeZion",  # ראשל"צ פרס נובל
        "031": "Tel Aviv",  # רוטשילד
        "083": "Rehovot",  # רחובות
        "021": "Ramla",  # רמלה
        "029": "Ramat Gan",  # רמת גן
        "053": "Ramat Yishai",  # רמת ישי
        "069": "Raanana",  # רעננה אחוזה
        "074": "Herzliya",  # שבעת הכוכבים
        "003": "Sderot",  # שדרות
        "091": "Shoham",  # שוהם
        "094": "Rishon LeZion",  # שמוטקין
        "027": "Haifa",  # שער עליה חיפה
        "050": "Tel Mond"  # תל מונד
        }
    }
    return store_cities.get(chain_id, {}).get(store_id, "Unknown")

def get_or_create_store(db_session, snif_key: str, chain: str) -> Store:
    """Get existing store or create new one"""
    store = db_session.query(Store).filter(Store.snif_key == snif_key).first()

    if not store:
        city = get_store_city(snif_key)
        store = Store(
            snif_key=snif_key,
            chain=chain,
            city=city,
            store_name=f"{chain} - {snif_key}"
        )
        db_session.add(store)
        db_session.flush()  # Get the store ID

    return store

def save_prices_to_db(chain: str, prices_data: List[tuple]):
    """Save prices to PostgreSQL database"""
    with get_db() as db:
        try:
            # Group prices by store
            prices_by_store = {}
            for snif_key, item_code, item_name, item_price in prices_data:
                if snif_key not in prices_by_store:
                    prices_by_store[snif_key] = []
                prices_by_store[snif_key].append((item_code, item_name, item_price))

            # Process each store
            for snif_key, store_prices in prices_by_store.items():
                # Get or create store
                store = get_or_create_store(db, snif_key, chain)

                # Delete old prices for this store (optional - you might want to keep history)
                db.query(Price).filter(Price.store_id == store.id).delete()

                # Add new prices
                for item_code, item_name, item_price in store_prices:
                    price = Price(
                        store_id=store.id,
                        item_code=item_code,
                        item_name=item_name,
                        item_price=item_price,
                        timestamp=datetime.utcnow()
                    )
                    db.add(price)

                logger.info(f"Saved {len(store_prices)} items for store {snif_key}")

            db.commit()
            logger.info(f"Successfully saved all {chain} prices to database")

        except Exception as e:
            logger.error(f"Error saving prices: {str(e)}")
            db.rollback()
            raise


# Function to download and extract GZ file
def download_and_extract_gz(url):
    response = requests.get(url)
    if response.status_code == 200:
        with gzip.GzipFile(fileobj=BytesIO(response.content)) as f:
            return f.read()  # Return raw XML content
    print(f"❌ Failed to download: {url}")
    return None

# Function to parse Shufersal XML
def parse_shufersal_xml(xml_content):
    root = ET.fromstring(xml_content)
    prices_data = []

    for item in root.findall(".//Item"):
        snif_key = f"{root.find('ChainId').text}-{root.find('SubChainId').text}-{root.find('StoreId').text}"
        item_code = item.find('ItemCode').text
        item_name = item.find('ItemName').text
        item_price = float(item.find('ItemPrice').text)
        prices_data.append((snif_key, item_code, item_name, item_price))

    return prices_data

# Function to parse Victory XML
def parse_victory_xml(xml_content):
    root = ET.fromstring(xml_content)
    prices_data = []

    chain_id = root.find("ChainID").text
    sub_chain_id = root.find("SubChainID").text
    store_id = root.find("StoreID").text
    snif_key = f"{chain_id}-{sub_chain_id}-{store_id}"

    for product in root.findall(".//Product"):
        item_code = product.find("ItemCode").text
        item_name = product.find("ItemName").text
        item_price = float(product.find("ItemPrice").text)
        prices_data.append((snif_key, item_code, item_name, item_price))

    return prices_data


# Scraper for Shufersal
def scrape_shufersal():
    logger.info("Starting Shufersal scraping...")
    base_url = 'https://prices.shufersal.co.il/FileObject/UpdateCategory?catID=2&storeId=0&page='
    page_num = 1
    all_prices = []

    while page_num < 21:  # Limit pages as before
        page_url = base_url + str(page_num)
        response = requests.get(page_url)

        if response.status_code == 200:
            soup = BeautifulSoup(response.text, 'html.parser')
            links = soup.find_all('a', text='לחץ להורדה')

            if not links:
                logger.info(f"No more pages at page {page_num}")
                break

            for link in links:
                download_url = link.get('href')
                if download_url:
                    logger.info(f"Downloading: {download_url}")
                    xml_content = download_and_extract_gz(download_url)
                    if xml_content:
                        prices_data = parse_shufersal_xml(xml_content)
                        all_prices.extend(prices_data)

            page_num += 1
        else:
            logger.error(f"Failed to fetch Shufersal page {page_num}")
            break

    # Save all prices to PostgreSQL
    if all_prices:
        save_prices_to_db('shufersal', all_prices)
        logger.info(f"Completed Shufersal scraping: {len(all_prices)} total prices")


def scrape_victory():
    logger.info("Starting Victory scraping...")
    page_url = "https://laibcatalog.co.il/NBCompetitionRegulations.aspx?code=7290696200003&fileType=pricefull"
    all_prices = []

    response = requests.get(page_url)
    if response.status_code != 200:
        logger.error("Failed to fetch Victory page")
        return

    soup = BeautifulSoup(response.text, 'html.parser')
    links = soup.find_all('a', string='לחץ כאן להורדה')

    if not links:
        logger.error("No download links found for Victory")
        return

    base_url = "https://laibcatalog.co.il/"

    for link in links:
        relative_url = link.get('href')
        if relative_url:
            download_url = base_url + relative_url
            logger.info(f"Downloading: {download_url}")
            xml_content = download_and_extract_gz(download_url)
            if xml_content:
                prices_data = parse_victory_xml(xml_content)
                all_prices.extend(prices_data)

    # Save all prices to PostgreSQL
    if all_prices:
        save_prices_to_db('victory', all_prices)
        logger.info(f"Completed Victory scraping: {len(all_prices)} total prices")
