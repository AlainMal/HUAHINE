""" CONSTANTES """
# Variables systèmes sur PC
ES_CONTINUOUS = 0x80000000
ES_SYSTEM_REQUIRED = 0x00000001
ES_DISPLAY_REQUIRED = 0x00000002

# Constante pour initialiser le bus CAN
CAN_BAUD_250K = b"250"
CANUSB_ACCEPTANCE_CODE_ALL = 0x0
CANUSB_ACCEPTANCE_MASK_ALL = 0xFFFFFFFF
FLUSH_WAIT = 0x0
FLUSH_DONTWAIT = 0x1
CANUSB_FLAG_TIMESTAMP = 0x1

# Constante pour initialiser l'émission le bus CAN USB étendu
CAN_EXTENDED = 0x80

# Erreur de retour
CANUSB_OK = 1                          # All is OK
ERROR_CANUSB_OPEN_SUBSYSTEM = -2       # Problems with a driver subsystem
ERROR_CANUSB_COMMAND_SUBSYSTEM = -3    # Unable to send command to adapter
ERROR_CANUSB_NOT_OPEN = -4             # Channel doesn't open
ERROR_CANUSB_TX_FIFO_FULL = -5         # Transmit fifo full
ERROR_CANUSB_INVALID_PARAM = -6        # Invalid parameter
ERROR_CANUSB_NO_MESSAGE = -7           # No message available

# Résultat du status CAN
CANSTATUS_NO_ERROR = 0x0
CANSTATUS_NO_CONNECT = -1
CANSTATUS_RECEIVE_FIFO_FULL = 0x1
CANSTATUS_TRANSMIT_FIFO_FULL = 0x2
CANSTATUS_ERROR_WARNING = 0x4
CANSTATUS_DATA_OVERRUN = 0x8
CANSTATUS_ERROR_PASSIVE = 0x20
CANSTATUS_ARBITRATION_LOST = 0x40
CANSTATUS_BUS_ERROR = 0x80



# Liste des PGN nécessitant la mise en mémoire
PGN_129038 = 0
PGN_129039 = 1
PGN_127506 = 2
PGN_126464 = 3
# Liste à compléter...

# Liste des huit octets
MEMOIRE_PGN_a0 = 0
MEMOIRE_PGN_a1 = 1
MEMOIRE_PGN_a2 = 2
MEMOIRE_PGN_a3 = 3
MEMOIRE_PGN_a4 = 4
MEMOIRE_PGN_a5 = 5
MEMOIRE_PGN_a6 = 6
MEMOIRE_PGN_a7 = 7

# ------------------------- Dictionnaires des significations des valeurs reçues dans les tables ------------------------
# Table des températures.
TEMPERATURE = {
0:	"Température de la mer",
1:	"Température extérieure",
2:	"Température intérieure",
3:	"Température de la salle des machines",
4:	"Température de la cabine principale",
5:	"Température du vivier",
6:	"Température du puits d’appât",
7:	"Température de réfrigération",
8:	"Température du système de chauffage",
9:	"Température du point de rosée",
10:	"Température apparente de refroidissement éolien",
11:	"Température théorique de refroidissement éolien",
12:	"Indice de chaleur Température",
13:	"Température du congélateur",
14:	"Température des gaz d’échappement",
15:	"Température du joint d’arbre"
}

# Table des vents.
VENT = {
    0: "Vent Ground",
    1: "Vent Magnétique",
    2: "Vent Apparent",
    3: "Vent Vrai Fond",
    4: "Vent Vrai"
}

# Table des vitesses sur l'eau.
WATER_SPEED ={
0:	"Roue à aubes",
1:	"Tube de Pitot",
2:	"Doppler",
3:	"Corrélation (ultrasons)",
4:	"Électromagnétique"
}

# Table des niveaux des réservoirs.
RESERVOIR = {
0:	"Combustible",
1:	"Eau",
2:	"Eaux grises",
3:	"Bien vivre",
4:	"Huile",
5:	"Eaux noires"
}

# Table des pressions.
PRESSION ={
0:	"Atmosphérique",
1:	"Eau",
2:	"Vapeur",
3:	"Air comprimé",
4:	"Hydraulique",
5:	"Filtre",
6:	"AltimètreRéglage",
7:	"Huile",
8:	"Combustible"
}

# Table de l'XTE.
MODE_XTE ={
0:	"Autonome",
1:	"Différentiel amélioré",
2:	"Estimatif",
3:	"Simulateur",
4:	"Manuelle"
}

# Table de source d'énergie.
ENERGIE_DC ={
0:	"Batterie",
1:	"Alternateur",
2:	"Convertisseur",
3:	"photovoltaïque",
4:	"Eolienne"
}

MANUFACTURE ={
69:	    "ARKS Enterprises, Inc.",
78:	    "FW Murphy/Enovation Controls",
80:	    "Twin Disc",
85:	    "Kohler Power Systems",
88:	    "Hemisphere GPS Inc",
116:	"BEP Marine",
135:	"Airmar",
137:	"Maretron",
140:	"Lowrance",
144:	"Mercury Marine",
147:	"Nautibus Electronic GmbH",
148:	"Blue Water Data",
154:	"Westerbeke",
157:	"ISSPRO Inc",
161:	"Offshore Systems (UK) Ltd.",
163:	"Evinrude/BRP",
165:	"CPAC Systems AB",
168:	"Xantrex Technology Inc.",
169:	"Marlin Technologies, Inc.",
172:	"Yanmar Marine",
174:	"Volvo Penta",
175:	"Honda Marine",
176:	"Carling Technologies Inc. (Moritz Aerospace)",
185:	"Beede Instruments",
192:	"Floscan Instrument Co. Inc.",
193:	"Nobletec",
198:	"Mystic Valley Communications",
199:	"Actia",
200:	"Honda Marine",
201:	"Disenos Y Technologia",
211:    "Digital Switching Systems",
215:	"Xintex/Atena",
224:	"EMMI NETWORK S0.L.",
225:	"Honda Marine",
228:	"ZF",
229:	"Garmin",
233:	"Yacht Monitoring Solutions",
235:	"Sailormade Marine Telemetry/Tetra Technology LTD",
243:	"Eride",
250:	"Honda Marine",
257:	"Honda Motor Company LTD",
272:	"Groco",
273:	"Actisense",
274:	"Amphenol LTW Technology",
275:	"Navico",
283:	"Hamilton Jet",
285:	"Sea Recovery",
286:	"Coelmo SRL Italy",
295:	"BEP Marine",
304:	"Empir Bus",
305:	"NovAtel",
306:	"Sleipner Motor AS",
307:	"MBW Technologies",
311:	"Fischer Panda",
315:	"ICOM",
328:	"Qwerty",
329:	"Dief",
341:	"Boening Automationstechnologie GmbH & Co. KG",
351:	"Thrane and Thrane",
355:	"Mastervolt",
356:	"Fischer Panda Generators",
358:	"Victron Energy",
370:	"Rolls Royce Marine",
373:	"Electronic Design",
374:	"Northern Lights",
378:	"Glendinning",
381:	"B & G",
384:	"Rose Point Navigation Systems",
385:	"Johnson Outdoors Marine Electronics Inc Geonav",
394:	"Capi 2",
396:	"Beyond Measure",
400:	"Livorsi Marine",
404:	"ComNav",
409:	"Chetco",
419:	"Fusion Electronics",
421:	"Standard Horizon",
422:	"True Heading AB",
426:	"Egersund Marine Electronics AS",
427:	"em-trak Marine Electronics",
431:	"Tohatsu Co, JP",
437:	"Digital Yacht",
438:	"Comar Systems Limited",
440:	"Cummins",
443:	"VDO (aka Continental-Corporation)",
451:	"Parker Hannifin aka Village Marine Tech",
459:	"Alltek Marine Electronics Corp",
460:	"SAN GIORGIO S.E.I.N",
466:	"Veethree Electronics & Marine",
467:	"Humminbird Marine Electronics",
470:	"SI-TEX Marine Electronics",
471:	"Sea Cross Marine AB",
475:	"GME aka Standard Communications Pty LTD",
476:	"Humminbird Marine Electronics",
478:	"Ocean Sat BV",
481:	"Chetco Digitial Instruments",
493:	"Watcheye",
499:	"Lcj Capteurs",
502:	"Attwood Marine",
503:	"Naviop S.R.L.",
504:	"Vesper Marine Ltd",
510:	"Marinesoft Co. LTD",
513:	"Simarine",
517:	"NoLand Engineering",
518:	"Transas USA",
529:	"National Instruments Korea",
530:	"National Marine Electronics Association",
532:	"Onwa Marine",
540:	"Webasto",
571:    "Marinecraft (South Korea)",
573:	"McMurdo Group aka Orolia LTD",
578:	"Advansea",
579:    "KVH",
580:	"San Jose Technology",
583:	"Yacht Control",
586:	"Suzuki Motor Corporation",
591:	"US Coast Guard",
595:	"Ship Module aka Customware",
600:	"Aquatic AV",
605:	"Aventics GmbH",
606:	"Intellian",
612:	"SamwonIT",
614:	"Arlt Tecnologies",
637:	"Bavaria Yacts",
641:	"Diverse Yacht Services",
644:	"Wema U.S.A dba KUS",
645:	"Garmin",
658:	"Shenzhen Jiuzhou Himunication",
688:	"Rockford Corp",
699:	"Harman International",
704:	"JL Audio",
708:	"Lars Thrane",
715:	"Autonnic",
717:	"Yacht Devices",
734:	"REAP Systems",
735:	"Au Electronics Group",
739:	"LxNav",
741:	"Littelfuse, Inc (formerly Carling Technologies)",
743:	"DaeMyung",
744:	"Woosung",
748:	"ISOTTA IFRA srl",
773:	"Clarion US",
776:	"HMI Systems",
777:	"Ocean Signal",
778:	"Seekeeper",
781:	"Poly Planar",
785:	"Fischer Panda DE",
795:	"Broyda Industries",
796:	"Canadian Automotive",
797:	"Tides Marine",
798:	"Lumishore",
799:	"Still Water Designs and Audio",
803:	"Gill Sensors",
811:	"Blue Water Desalination",
815:	"FLIR",
824:	"Undheim Systems",
826:	"Lewmar Inc",
838:	"TeamSurv",
844:	"Fell Marine",
847:	"Oceanvolt",
862:	"Prospec",
868:	"Data Panel Corp",
890:    "L3 Technologies",
894:	"Rhodan Marine Systems",
896:	"Nexfour Solutions",
905:    "ASA Electronics",
909:	"Marines Co (South Korea)",
911:	"Nautic-on",
917:	"Sentinel",
929:	"JL Marine ystems",
930:	"Ecotronix",
944:	"Zontisa Marine",
951:	"EXOR International",
962:	"Timbolier Industries",
963:    "TJC Micro",
968:	"Cox Powertrain",
981:	"Kobelt Manufacturing Co. Ltd",
992:	"Blue Ocean IOT",
997:	"Xenta Systems",
1004:	"Ultraflex SpA",
1008:	"Lintest SmartBoat",
1011:	"Soundmax",
1020:	"Team Italia Marine (Onyx Marine Automation s.r.l)",
1021:	"Entratech",
1022:	"ITC Inc.",
1029:	"The Marine Guardian LLC",
1047:	"Sonic Corporation",
1051:	"ProNav",
1053:	"Vetus Maxwell INC.",
1056:	"Lithium Pros""",
1059:	"Boatrax",
1062:	"Marol Co ltd",
1065:	"CALYPSO Instruments",
1066:	"Spot Zero Water",
1069:	"Lithionics Battery LLC",
1070:	"Quick-teck Electronics Ltd",
1075:	"Uniden America",
1083:	"Nauticoncept",
1084:	"Shadow-Caster LED lighting LLC",
1085:	"Wet Sounds, LLC",
1088:	"E-T-A Circuit Breakers",
1092:	"Scheiber",
1100:	"Smart Yachts International Limited",
1114:	"Bobs Machine",
1118:   "L3Harris ASV",
1119:	"Balmar LLC",
1120:	"Elettromedia spa",
1127:	"Electromaax",
1140:	"Across Oceans Systems Ltd.",
1145:	"Kiwi Yachting",
1150:	"BSB Artificial Intelligence GmbH",
1151:	"Orca Technologoes AS",
1154:	"TBS Electronics BV",
1158:	"Technoton Electroics",
1160:	"MG Energy Systems B.V.",
1169:	"Sea Macine Robotics Inc.",
1171:	"Vista Manufacturing",
1183:	"Zipwake",
1186:	"Sailmon BV",
1192:	"Airmoniq Pro Kft",
1194:	"Sierra Marine",
1200:	"Xinuo Information Technology (Xiamen)",
1218:	"Septentrio",
1233:	"NKE Marine Elecronics",
1238:	"SuperTrack Aps",
1239:	"Honda Electronics Co., LTD",
1245:	"Raritan Engineering Company, Inc",
1249:	"Integrated Power Solutions AG",
1260:	"Interactive Technologies, Inc.",
1283:	"LTG-Tech",
1299:	"Energy Solutions (UK) LTD.",
1300:	"WATT Fuel Cell Corp",
1302:	"Pro Mainer",
1305:	"Dragonfly Energy",
1306:	"Koden Electronics Co., Ltd",
1311:	"Humphree AB",
1316:	"Hinkley Yachts",
1317:	"Global Marine Management GmbH (GMM)",
1320:	"Triskel Marine Ltd",
1330:	"Warwick Control Technologies",
1331:	"Dolphin Charger",
1337:	"Barnacle Systems Inc",
1348:	"Radian IoT, Inc.",
1353:	"Ocean LED Marine Ltd",
1359:	"BluNav",
1361:	"OVA (Nantong Saiyang Electronics Co., Ltd)",
1368:	"RAD Propulsion",
1369:	"Electric Yacht",
1372:	"Elco Motor Yachts",
1384:	"Tecnoseal Foundry S.r.l",
1385:	"Pro Charging Systems, LLC",
1389:	"EVEX Co., LTD",
1398:	"Gobius Sensor Technology AB",
1403:	"Arco Marine",
1408:	"Lenco Marine Inc.",
1413:	"Naocontrol S.L.",
1417:	"Revatek",
1438:	"Aeolionics",
1439:	"PredictWind Ltd",
1440:	"Egis Mobile Electric",
1445:	"Starboard Yacht Group",
1446:	"Roswell Marine",
1451:	"ePropulsion (Guangdong ePropulsion Technology Ltd.)",
1452:	"Micro-Air LLC",
1453:	"Vital Battery",
1458:	"Ride Controller LLC",
1460:	"Tocaro Blue",
1461:	"Vanquish Yachts",
1471:	"FT Technologies",
1478:	"Alps Alpine Co., Ltd.",
1481:	"E-Force Marine",
1482:	"CMC Marine",
1483:	"Nanjing Sandemarine Information Technology Co., Ltd.",
1850:	"Teleflex Marine (SeaStar Solutions)",
1851:	"Raymarine",
1852:	"Navionics",
1853:	"Japan Radio Co",
1854:	"Northstar Technologies",
1855:	"Furuno",
1856:	"Trimble",
1857:	"Simrad",
1858:	"Litton",
1859:	"Kvasar AB",
1860:	"MMP",
1861:	"Vector Cantech",
1862:	"Yamaha Marine",
1863:	"Faria Instruments"
}

# A compléter...