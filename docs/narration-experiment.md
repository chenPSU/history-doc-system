# ทดลอง 5 รอบ: การเล่าที่ดึงดูดและฟังซ้ำได้

Nov 19, 2026 · @Chen

## สรุปผล

&#91;embedded content: score.py · บทตัวอย่าง v0–v5 · วัดซ้ำทุกฉบับหลังรอบ 5\]

บทตัวอย่างคือตอน Constantinople 1453 ของช่องอังกฤษ ยาวราว 6.6 นาที แต่ละรอบค้นงานวิจัย 1 ด้าน เพิ่มตัววัดด้านนั้น แก้บท แล้ววัดทุกฉบับย้อนหลังด้วยตัววัดชุดเดียวกัน

**คันโยกที่ได้ผลที่สุดจากแต่ละรอบ**

1. **Hook:** เปิดกลางเหตุการณ์ บอกตอนจบที่คนรู้อยู่แล้ว แล้วถามว่า "อย่างไร"
2. **เขียนเพื่อหู:** 1 ประโยค 1 ความคิด 1 ตัวเลข และตามประโยคยาวด้วยประโยคสั้น
3. **แรงขับเรื่อง:** เชื่อมจังหวะด้วย but/so ใส่อุปสรรคจริงทุกบท และจบบทด้วยคำถามถัดไป
4. **เสียง:** เพลงบรรเลงเท่านั้น เบากว่าเสียงพูดราว 20 dB ใช้ J/L-cut ทุกรอยต่อ และเงียบก่อนจุดพีค
5. **ฟังซ้ำ:** ตอนจบตอบคำถามใน hook ใบ้ตอนถัดไปเป็นคำถาม และปิดด้วยคำประจำช่อง

**สิ่งที่ไม่คาดคิด:** ตอนแก้ประโยคให้สั้นในรอบ 2 บทมีประโยคที่ขึ้นต้นด้วย "Then…" เพิ่มขึ้น คะแนนแรงขับเรื่องจึงตกจาก 45.2 เหลือ 28.2 การตัดประโยคกับการเชื่อมจังหวะจึงต้องทำพร้อมกัน อีกจุดคือการพูดกับผู้ชมใน hook ทำให้คำถามแรกมาช้าลง ต้องย้ายไปหลังคำถาม

**อ่านตัวเลขนี้อย่างระวัง:** คะแนนวัดว่าบททำตามกฎครบแค่ไหน ไม่ใช่คนดูจะดูนานแค่ไหน ผมเป็นคนออกแบบทั้งตัววัดและบทที่แก้ คะแนนจึงขึ้นง่ายกว่าความจริง (ดูหัวข้อข้อจำกัด) คำตอบจริงคือกราฟ retention และคนดูที่กลับมาดูซ้ำหลังลงคลิปจริง

## วิธีทดลองและวัดผล

**บทที่ใช้ทดสอบ:** ตอน Constantinople (สัปดาห์ 14 ธ.ค. ใน Roadmap) ตัดมาเฉพาะโครงหลักของคลิป: Hook · Promise · Context · Chapter 1 · Turning point · Close (ราว 5–7 นาที) v0 คือบทร่างแบบที่คนทั่วไปมักเขียนก่อนใช้เทคนิคใดๆ (ประโยคยาวแบบสารานุกรม ไล่หัวข้อ จบด้วย like and subscribe) แต่ละรอบแก้จากฉบับก่อนหน้า ได้ v1–v5

**1 รอบ = 4 ขั้น**

1. **ค้นคว้า** งานวิจัยและแนวปฏิบัติด้านเดียว (จิตวิทยา โฆษณา หนัง หรือข้อมูล YouTube)
2. **วัดผล** แปลงข้อค้นพบเป็นตัววัดที่คำนวณได้จากตัวบท เพิ่มในสคริปต์ score.py แล้ววัดฉบับปัจจุบัน
3. **แก้ไข** แก้เฉพาะด้านของรอบนั้น แล้ววัดซ้ำ รวมทั้งตัววัดของรอบก่อนทุกรอบ เพื่อดูว่าการแก้ไม่ทำให้สิ่งที่ดีอยู่แล้วเสีย
4. **รายงาน** ผลก่อน-หลัง สิ่งที่แก้ ข้อสังเกต และกฎที่ได้ลงเอกสารนี้

**วิธีคิดคะแนน:** แต่ละตัววัดมีเป้าหมาย ได้ 1.0 เมื่ออยู่ในเป้า และลดลงตามระยะที่ห่างจากเป้า คะแนนรอบ = ค่าเฉลี่ยตัววัดของรอบนั้น × 100 คำนวณเวลาจากความเร็วพูด 150 คำ/นาที บรรทัดในวงเล็บ \[ \] เป็นคำสั่งงานภาพ/เสียง ไม่นับเป็นคำบรรยาย หลังจบรอบ 5 วัดทุกฉบับใหม่ด้วยตัววัดชุดสุดท้าย (36 ข้อ) ตัวเลขในกราฟสรุปจึงเทียบกันได้ตรงๆ ตัวเลขในตารางรายรอบคือค่าตอนทำรอบนั้น

**บั๊กของตัววัดที่พบและแก้ระหว่างทาง (4 จุด):** ", and" นับหัวข้อซ้ำ · วันที่และ "seven thousand" ถูกนับเป็นหลายตัวเลข · ตัวจับชื่อคนนับ "Inside" กับ "May" · ตัวจับใบ้ตอนถัดไปอ่าน "How" ตัวพิมพ์ใหญ่ไม่ออก แก้แล้ววัดทุกฉบับใหม่ทุกครั้ง มี 1 จุดที่เปลี่ยนขอบเขตตัววัดก่อนวัดฉบับใหม่: "จบด้วย loop เปิด" ไม่นับส่วนจุดพีค

## รอบ 1: Hook และ 30 วินาทีแรก

**ค้นคว้า**

- YouTube Studio วัดค่า **Intro** คือสัดส่วนคนที่ยังดูอยู่หลัง 30 วินาทีแรก ค่านี้สูงมักแปลว่าช่วงเปิดตรงกับที่ title และ thumbnail สัญญาไว้ ([YouTube Help](https://support.google.com/youtube/answer/1715160?hl=en)) คู่มือหลายแหล่งใช้เกณฑ์ว่าถ้าเสียคนเกิน 40% ใน 30 วินาทีแรก ช่วงเปิดต้องแก้ ([Opus](https://www.opus.pro/blog/youtube-retention-graphs-explained))
- การไล่หัวข้อทุกบทในช่วงเปิดไม่ใช่แผนที่นำทาง แต่เป็นการเฉลยล่วงหน้า บอกบรรทัดเดียวก็พอ และไม่ควรเปิดด้วยคำทักทายหรือชื่อช่อง ([OutlierKit](https://outlierkit.com/resources/youtube-hooks-and-retention/))
- เทคนิคหนัง **cold open / in medias res** คือเปิดกลางเหตุการณ์ก่อนให้บริบท แล้วสร้างคำถามให้คนอยากรู้คำตอบ ([Fiveable](https://library.dev.fiveable.me/writing-the-television-pilot/unit-4/cold-opens-teasers/study-guide/q5MxpMT8ByQK1nMJ))
- **การรู้ตอนจบไม่ได้ทำลายเรื่อง:** Leavitt & Christenfeld (2011) พบว่าคนชอบเรื่องที่ถูกเฉลยล่วงหน้ามากกว่า แต่งานทำซ้ำรุ่นหลังพบว่าไม่ได้เพิ่มความชอบ และบางกรณีลดความลุ้น ([UC](https://www.universityofcalifornia.edu/news/spoiler-alert-spoilers-make-you-enjoy-stories-more), [งานทำซ้ำ](https://core.ac.uk/download/72840983.pdf)) ข้อสรุปสำหรับสารคดีประวัติศาสตร์ที่คนรู้ตอนจบอยู่แล้วคือ ให้ถาม **"ทำไม / อย่างไร"** แทน "จะเกิดอะไรขึ้น"

**ตัววัดที่เพิ่มในรอบนี้ (7 ข้อ):** เวลาจนถึงคำถามแรก (≤12 วินาที) · ความยาว Hook+Promise (20–40 วินาที) · ประโยคแรก ≤14 คำและเป็นภาพเจาะจง (เวลา/สถานที่/คน) · จำนวนหัวข้อที่ไล่ใน Promise (≤2) · คำเปิดต้องห้าม ("in this video", "welcome") · คำใน title/thumbnail ปรากฏใน 30 วินาทีแรก · คำถามเปิดเป็นแบบ how/why

**วัดผล**

| ตัววัด | v0 | v1 |
| --- | --- | --- |
| เวลาจนถึงคำถามแรก | 31.2 วิ | 20.0 วิ |
| Hook+Promise | 56 วิ | 40 วิ |
| ประโยคแรก | 14 คำ ไม่เจาะจง | 12 คำ มีวันเวลา |
| หัวข้อที่ไล่ใน Promise | 6 | 2 |
| คำเปิดต้องห้าม | 1 ("In this video") | 0 |
| ตรง title/thumbnail | ไม่มี title | 5/5 คำ |
| คะแนนรอบ 1 | **28.7** | **93.9** |

**สิ่งที่แก้**

- เปลี่ยนเปิดแบบบทนำทั่วไปเป็น cold open ตอนตีหนึ่งครึ่งของคืนสุดท้าย บอกตอนจบไปเลย ("By sunrise… will fall") แล้วตั้งคำถามว่า **อย่างไร**
- ตัด Promise ที่ไล่ 6 หัวข้อ เหลือ 2 ปริศนา (ปืนใหญ่ที่ไม่มีใครยอมจ่าย กับกองเรือที่ข้ามภูเขา) และเก็บความพลิกผันอื่นไว้เป็นเซอร์ไพรส์
- ตั้ง title "How 53 Days Broke a Thousand-Year Wall" กับ thumbnail "53 DAYS" แล้วให้คำเหล่านี้อยู่ในบทภายใน 30 วินาที

**ข้อสังเกต:** ระหว่างรอบพบบั๊กในตัวนับหัวข้อ (", and" ถูกนับซ้ำ) จึงแก้ตัววัดแล้วรันใหม่ทั้ง v0 และ v1 คำถามแรกยังมาที่ 20 วินาที ช้ากว่าเป้า แต่ประโยค "By sunrise… will fall" ที่วินาที \~14 เปิดช่องว่างไว้แล้วโดยไม่มีเครื่องหมายคำถาม ตัววัดนี้จึงเข้มกว่าความจริงเล็กน้อย

**กฎที่ได้:** เปิดกลางเหตุการณ์ด้วยวันเวลาและภาพเจาะจง · ตอนจบที่คนรู้แล้วให้เฉลยเลย แล้วถาม "อย่างไร" · Promise บรรทัดเดียว ไม่เกิน 2 ปริศนา · คำใน thumbnail ต้องได้ยินภายใน 30 วินาที

## รอบ 2: เขียนเพื่อหู ฟังลื่น

**ค้นคว้า**

- คู่มือข่าววิทยุ/ทีวีแทบทุกเล่มให้ **1 ประโยค 1 ความคิด** บางเล่มแนะนำ 8–12 คำต่อประโยค ([Human Kinetics](https://canada.humankinetics.com/blogs/excerpt/tips-for-writing-for-broadcast)) บางเล่มวางเพดาน 20 คำ ([The News Manual](https://thenewsmanual.net/Manuals%20Volume%202/volume2_48.htm)) เหตุผลคือคนฟังย้อนกลับไปอ่านซ้ำไม่ได้ ([IJNet](https://ijnet.org/es/node/4312))
- ถ้ามีประโยคยาว ให้ตามด้วยประโยคสั้น ใช้ active voice และใส่ผู้พูดก่อนคำพูด ([IJNet](https://ijnet.org/en/story/broadcast-writing-tips), [Mervin Block](https://mervinblock.com/?p=37))
- **ความเร็วพูด:** นักพากย์หนังสือเสียงเฉลี่ย 150–160 คำ/นาที ([คู่มือหนังสือเสียง](https://sites.google.com/view/snowdaycaculators/audiobook-narration-speed-explained-what-150-160-wpm-really-means)) การฟังเข้าใจไม่ลดลงจนถึงราว 270 คำ/นาที ([McMaster](https://experts.mcmaster.ca/scholarly-works/2127220)) แต่งานวิจัยโฆษณาเสียงเตือนว่าการอัดข้อมูลด้วยความเร็วสูงควรเลี่ยง ([WARC](https://cdn.warc.com/newsandopinion/news/how-speech-delivery-speed-impacts-audio-ads/43304)) ข้อสรุปคือความเร็วไม่ใช่ปัญหา ความหนาแน่นของประโยคคือปัญหา จึงคง 150 คำ/นาทีไว้สำหรับโหมดฟังเพลิน

**ตัววัดที่เพิ่ม (9 ข้อ):** ความยาวประโยคเฉลี่ย · % ประโยคเกิน 20 คำ · ประโยคยาวสุด · Flesch reading ease · passive voice · ประโยคที่มีตัวเลข 2 ตัวขึ้นไป · อนุประโยคซ้อน (which/whom) · ประโยคยาวตามด้วยประโยคสั้น · ความหลากหลายของความยาว (CV) กันบทสั้นเท่ากันทุกประโยคจนซ้ำซาก

**วัดผล**

| ตัววัด | v1 | v2 |
| --- | --- | --- |
| ความยาวเฉลี่ย (คำ) | 21.4 | 8.6 |
| ประโยคเกิน 20 คำ | 46.9% | 1.3% |
| ประโยคยาวสุด | 51 คำ | 23 คำ (CTA) |
| Flesch reading ease | 53.9 | 74.6 |
| passive ต่อ 10 ประโยค | 1.88 | 0.39 |
| ประโยคตัวเลขแน่น | 4 | 1 |
| ประโยคยาวตามด้วยสั้น | 5% | 100% |
| CV ความยาว | 0.48 | 0.45 |
| คะแนนรอบ 2 | **41.2** | **97.8** |

**สิ่งที่แก้** (ตัวอย่าง)

- ก่อน (51 คำ): "The city was protected by water on three sides and by the Theodosian Walls on the fourth, a system of moat, outer wall and inner wall stretching around 5.7 kilometres from the Sea of Marmara to the Golden Horn, which was constructed…"
- หลัง: "Water protected the city on three sides. On the fourth side stood the Theodosian Walls. They were not one wall, but three layers. First a moat. Then an outer wall. Then a taller inner wall behind it."
- ปัดตัวเลข (5.7 กม. → "almost six kilometres") แยกตัวเลขให้อยู่คนละประโยค เปลี่ยน passive เป็น active ("his body was never identified" → "No one ever identified his body")

**ข้อสังเกต:** แก้ตัวนับตัวเลขให้นับวันที่ (29 May 1453) และ "seven thousand" เป็น 1 ข้อมูล แล้วรันใหม่ทุกฉบับ คำถามใน hook ยังมี 2 ตัวเลข (พันปี กับ 53 วัน) ซึ่งตั้งใจให้เป็นคู่เทียบ ความยาวเฉลี่ย 8.6 คำเกือบต่ำกว่าเกณฑ์ ถ้าสั้นกว่านี้จะฟังเหมือนหุ่นยนต์

**กฎที่ได้:** เฉลี่ย 8–16 คำ ไม่เกิน 28 คำ · 1 ประโยค 1 ตัวเลข (ยกเว้นคู่เทียบที่ตั้งใจ) · ปัดตัวเลข · ประโยคยาวต้องตามด้วยประโยคสั้น · active voice · อ่านออกเสียงก่อนส่งทุกครั้ง

## รอบ 3: แรงขับของเรื่องและการดึงกลับกลางคลิป

**ค้นคว้า**

- **กฎ but/therefore:** Trey Parker และ Matt Stone บอกว่าถ้าคำที่เชื่อมระหว่างจังหวะของเรื่องคือ "and then" เรื่องจะน่าเบื่อ ระหว่างทุกจังหวะควรเป็น "therefore" หรือ "but" ([Cheat Sheet](https://www.cheatsheet.com/entertainment/south-park-trey-parker-and-matt-stone-1-rule.html/), [No Film School](https://nofilmschool.com/2015/04/tony-zhou-storytelling-video-essay-f-fake-therefore-but-and-then))
- **ความลุ้นทั้งที่รู้ตอนจบ (anomalous suspense):** งานทดลองของ Gerrig พบว่าคนอ่านเกิดความไม่แน่ใจได้แม้กับเหตุการณ์ที่รู้ผลแน่นอน (เช่น จอร์จ วอชิงตันจะได้เป็นประธานาธิบดีไหม) เมื่อเรื่องใส่ **อุปสรรค** ต่อผลลัพธ์นั้น ([Stony Brook](https://researchconnect.stonybrook.edu/en/publications/suspense-in-the-absence-of-uncertainty/), [Bordwell](https://www.davidbordwell.net/blog/?p=300)) นี่คือกุญแจของสารคดีประวัติศาสตร์
- **การดึงกลับกลางคลิป:** คู่มือหลายแหล่งแนะให้ปิดคำถามหนึ่งแล้วเปิดคำถามใหม่ทันที และบอกใบ้ส่วนถัดไปทุก 2–3 นาที ([Overseer](https://www.overseeros.com/blog/addictive-storytelling-youtube), [OutlierKit](https://outlierkit.com/resources/youtube-hooks-and-retention/)) และต้องปิดทุก loop ที่เปิด ไม่งั้นคนดูจะเลิกเชื่อคำสัญญาครั้งต่อไป ([TubeMilestone](https://tubemilestone.com/blog/longer-youtube-videos-retention))

**ตัววัดที่เพิ่ม (6 ข้อ):** จำนวน "and then" ระหว่างจังหวะ (0) · คำเชื่อม but/so/still ต่อนาที (≥2) · ทุกส่วนเนื้อเรื่องมีอุปสรรคชัด · ทุกส่วนก่อนจุดพีคจบด้วย loop ที่เปิด · ช่วงยาวสุดที่ไม่มีคำถามหรือคำใบ้ (≤90 วินาที) · คนที่มีชื่อและมีสิ่งที่ต้องการ (≥3 คน)

**วัดผล**

| ตัววัด | v2 | v3 |
| --- | --- | --- |
| "and then" ระหว่างจังหวะ | 7 | 0 |
| but/therefore ต่อนาที | 1.57 | 3.43 |
| ส่วนที่มีอุปสรรค | 1/3 | 3/3 |
| จบด้วย loop เปิด | 1/4 | 4/4 |
| ช่วงยาวสุดไม่มีคำใบ้ | 242 วิ | 91 วิ |
| คนที่มีเป้าหมาย | Mehmed | Mehmed, Constantine, Halil |
| คะแนนรอบ 3 | **28.2** | **99.8** |

**สิ่งที่แก้**

- เปลี่ยนห่วงโซ่เหตุการณ์เป็นเหตุ-ผล: กำแพงแข็งเกินปืนที่มี **→ ดังนั้น** มหะหมัดรับช่างปืน Orban **→ แต่** ปืนยิงได้ไม่กี่นัดต่อวัน **→ ดังนั้น** ฝ่ายตั้งรับซ่อมกำแพงทุกคืน **→ แต่** เรือคริสเตียน 4 ลำฝ่าวงล้อมเข้ามาได้ **→ ดังนั้น** ลากเรือข้ามเขา
- เพิ่มอุปสรรคจริงที่ทำให้ผลดูไม่แน่นอน: การบุกวันที่ 18 เม.ย. ถูกตีกลับ · เรือ 4 ลำฝ่าวงล้อมเมื่อ 20 เม.ย. · สมุหนายก Halil เร่งให้ถอนทัพ → คนที่รู้ตอนจบก็ยังลุ้นได้
- ส่วนท้ายบทเปิดคำถามต่อ: "Which leaves the real question of this siege. How do you beat a city you cannot cut off?" และคำใบ้กลางบท "Few in the West took him seriously. They would soon regret it."

**ข้อสังเกต:** ตัวตรวจจับชื่อคนรุ่นแรกจับผิด (นับ "Inside" กับ "May" เป็นคน) จึงเขียนใหม่ก่อนสรุปผล ส่วนตัวเช็ก "จบด้วย loop เปิด" ไม่นับส่วน Turning point เพราะจุดพีคคือที่ที่ควรปิดเรื่อง บทยาวขึ้นจาก 4.4 เป็น 5.5 นาที เพราะต้องมีเนื้อเรื่องอุปสรรคเพิ่ม คะแนนรอบ 1–2 ไม่ลดลง

**กฎที่ได้:** ห้ามใช้ "and then" เชื่อมจังหวะ · ทุกส่วนต้องมีอุปสรรคที่ทำให้ตอนจบที่รู้อยู่แล้วดูไม่แน่นอน · จบทุกบทด้วยคำถามถัดไป · มีคำถามหรือคำใบ้ทุก 90 วินาที · ตัวละครหลักอย่างน้อย 3 คน แต่ละคนมีสิ่งที่ต้องการชัด

## รอบ 4: เสียง ดนตรี จังหวะ สำหรับฟังเป็นพื้นหลัง

**ค้นคว้า**

- **เพลงมีเนื้อร้องแย่งสมองส่วนภาษา:** งานทดลองปี 2023 พบว่าเพลงมีเนื้อทำให้ความจำและการอ่านเข้าใจแย่ลง (d ≈ −0.3) แต่เพลงบรรเลงไม่มีผลชัดเจน ([PMC](https://pmc.ncbi.nlm.nih.gov/articles/PMC10162369/)) สอดคล้องกับงานที่พบว่าเสียงมีเนื้อรบกวนการอ่านและการจำ ส่วนเพลงบรรเลงไม่รบกวน ([eScholarship](https://escholarship.org/uc/item/88n5x9m1)) เสียงบรรยายคือภาษา ดังนั้นเพลงใต้เสียงบรรยายต้องไม่มีเนื้อ
- **ระดับเสียง:** YouTube ปรับเสียงทุกคลิปให้เท่ากันราว −14 LUFS ([Sweetwater](https://www.sweetwater.com/insync/how-to-master-audio-for-youtube/)) แนวทางที่ใช้กันสำหรับสารคดีประวัติศาสตร์คือให้เพลงเบากว่าเสียงพูด 18–24 dB และลดเพลงลงอีกตอนอธิบายตัวเลขหรือเรื่องซับซ้อน ([Overseer](https://www.overseeros.com/blog/background-music-volume-under-voiceover)) ตัวเลขนี้เป็นแนวปฏิบัติของคนทำงาน ไม่ใช่งานวิจัย
- **การเว้นจังหวะ:** งานทดลองกับผู้เรียนภาษาอังกฤษชาวญี่ปุ่นพบว่าการเว้นที่ยาวขึ้น (450 ms) ช่วยให้ฟังเข้าใจขึ้น ส่วนการพูดช้าลงไม่จำเป็นต้องช่วย ([J-STAGE](https://www.jstage.jst.go.jp/article/arele/27/0/27_97/_article/-char/en)) ส่วนการเว้นนานเกิน 4 วินาทีทำให้คนฟังจับใจความยาก ([ScienceNordic](https://sciencenordic.com/forskningno-language-society--culture/the-art-behind-the-perfect-pause/1422970))
- **เทคนิคหนัง:** J-cut ให้เสียงฉากถัดไปมาก่อนภาพ ส่วน L-cut ให้เสียงเดิมลากต่อ ([TechSmith](https://www.techsmith.com/blog/how-to-edit-videos-l-cuts-and-j-cuts/)) และการสลับช่วงเร็วกับช่วงพักหายใจเป็นหนึ่งในรูปแบบที่ AIR พบในช่องคลิปยาวกลุ่มที่คนดูนานที่สุด ([AIR](https://air.io/en/youtube-hacks/advanced-retention-editing-cutting-patterns-that-keep-viewers-past-minute-8))

**ตัววัดที่เพิ่ม (7 ข้อ)** ตรวจชั้นคำสั่งงานเสียงในบท: ทุกส่วนมี cue เพลงของตัวเอง · เพลงทุก cue ไม่มีเนื้อ · รอยต่อมี J/L-cut หรือ sound bridge · เว้นจังหวะอย่างน้อย 1 ครั้งต่อส่วนและไม่เกิน 3 วินาที · สเปกมิกซ์ (เพลง 18–24 dB ใต้เสียงพูด ทั้งคลิป −14 LUFS) · คำที่ต้องดูจอถึงจะเข้าใจ ("as you can see") = 0 · เพลงเงียบก่อนเฉลยจุดพีค

**วัดผล**

| ตัววัด | v3 | v4 |
| --- | --- | --- |
| ส่วนที่มี cue เพลง | 0/5 | 5/5 |
| เพลงไม่มีเนื้อ | ไม่มี cue | ทุก cue |
| รอยต่อมี J/L-cut | 0/5 | 5/5 |
| การเว้นจังหวะ | 0 | 6 ครั้ง (1–2 วินาที) |
| สเปกมิกซ์ | ไม่มี | −20 dB / −14 LUFS |
| คำที่ต้องดูจอ | 0 | 0 |
| เพลงเงียบก่อนจุดพีค | ไม่ | ใช่ (ก่อนเฉลยเรือ 70 ลำ) |
| คะแนนรอบ 4 | **14.3** | **100** |

**สิ่งที่แก้:** เพิ่มชั้นคำสั่งงานเสียง 22 บรรทัดโดยไม่แตะคำบรรยาย เช่น เสียงตีเหล็กในโรงหล่อปืนเข้ามาก่อนภาพ Chapter 1 · เพลงเงียบ 2 วินาทีแล้วปืนนัดแรกดังก้อง · เสียงไม้ครูดท่อนซุงแล้วเงียบก่อนเฉลยว่าเรือออตโตมันอยู่ในอ่าวแล้ว · ธีมหลักกลับมาเบาๆ ตอนปิด

**ข้อสังเกต (สำคัญ):** คะแนน 100 ในรอบนี้บอกแค่ว่า **แผนเสียงครบ** ไม่ได้บอกว่าเสียงจริงฟังดี ตัววัดชุดนี้ง่ายที่สุดที่จะทำคะแนนได้เต็ม ต้องตรวจต่อหลังมิกซ์ด้วยเครื่องวัด LUFS และฟังผ่านลำโพงทีวีกับมือถือเบาๆ อีกอย่างคือเสียงคนที่หนึ่งจากบันทึกจริง (เช่น Nicolò Barbaro) ยังไม่ได้ใส่ เพราะต้องคัดคำแปลจากต้นฉบับก่อน ห้ามแต่งคำพูด

**กฎที่ได้:** เพลงบรรเลงเท่านั้น เพลงเปลี่ยนตามอารมณ์ของแต่ละบท · เพลง −18 ถึง −24 dB ใต้เสียงพูด ทั้งคลิป −14 LUFS · เว้น 1–2 วินาทีหลังข้อเท็จจริงใหญ่ ไม่เกิน 3 วินาที · ทุกรอยต่อใช้ J/L-cut · เงียบเพลงก่อนเฉลยจุดพีค · ปิดจอฟังแล้วต้องเข้าใจครบ

## รอบ 5: ฟังซ้ำ ความผูกพัน และซีรีส์

**ค้นคว้า**

- **Peak-end rule:** คนตัดสินประสบการณ์จากจุดที่เข้มที่สุดกับตอนจบ แทบไม่นับความยาว (duration neglect) ([Wikipedia](https://en.wikipedia.org/wiki/Peak%E2%80%93end_rule)) ตอนจบที่เป็น "like and subscribe" จึงเป็นความทรงจำสุดท้ายที่เสียเปล่า
- **การพูดกับผู้ชมตรงๆ:** งานทดลองของ Hartmann & Goldhoorn (N=198) พบว่าการพูดกับผู้ชมทำให้ประสบการณ์ parasocial เข้มข้นขึ้น ([VU](https://typeset.io/pdf/horton-and-wohl-revisited-exploring-viewers-experience-of-2x3qk052xt.pdf)) และงานปี 2024 กับผู้ชมข่าว (N=255) พบว่าความรู้สึกนี้เพิ่มทั้งความน่าเชื่อถือและความสนุก ([Haifa](https://cris.haifa.ac.il/en/publications/look-me-in-the-eyes-how-direct-address-affects-viewers-experience/)) คนที่ฟังพอดแคสต์หลายชั่วโมงต่อสัปดาห์ผูกพันกับผู้ดำเนินรายการมากกว่า ([The Podcast Host](https://www.thepodcasthost.com/business-of-podcasting/podcast-listeners-less-lonely/))
- **ทำไมคนดูซ้ำ:** Russell & Levy เรียกว่า volitional reconsumption คนกลับไปดูเรื่องเดิมเพื่อเห็นสิ่งใหม่และเข้าใจตัวเองมากขึ้น ([Ready Steady Cut](https://readysteadycut.com/2022/09/26/the-psychology-behind-rewatching)) ส่วน Derrick พบว่าเรื่องคุ้นเคยใช้พลังสมองน้อยและทำให้ผ่อนคลาย ([Stuyvesant Spectator](https://stuyspec.com/article/the-psychology-of-rewatching)) ความคาดเดาได้ของโครงและพิธีกรรมประจำช่องจึงเป็นข้อดี ไม่ใช่ข้อเสีย

**ตัววัดที่เพิ่ม (7 ข้อ):** ตอนจบย้อนกลับไปหา hook และตอบคำถาม · จุดพีคอยู่ที่ 60–85% ของคลิป · ไม่มี CTA ทั่วไปและประโยคสุดท้ายเป็นคำปิดประจำช่อง · คำว่า "you" 1–4 ครั้งต่อนาที · ใบ้ตอนถัดไปแบบเจาะจง · ชื่อที่ปูทางไว้ต้นเรื่องกลับมาตอนท้าย · ครบทุกส่วนของแม่แบบช่อง

**วัดผล**

| ตัววัด | v4 | v5 |
| --- | --- | --- |
| ตอนจบย้อนหา hook | คำซ้ำ 4 คำ ไม่ตอบคำถาม | ตอบตรงๆ "So that is how…" |
| จุดพีค | 77% | 70% |
| CTA ทั่วไป / คำปิดประจำช่อง | 2 ครั้ง / ไม่มี | 0 / มี |
| "you" ต่อนาที | 0.72 | 1.71 |
| ใบ้ตอนถัดไป | ไม่มี | มี (Mehmed สร้างเมืองหลวงใหม่) |
| คะแนนรอบ 5 | **60.3** | **100** |

**สิ่งที่แก้**

- เขียนตอนจบใหม่ให้ตอบคำถามใน hook ตรงๆ แล้วสรุป 3 สาเหตุใน 3 ประโยคสั้น (ปืน · เรือข้ามเขา · Giustiniani ถอนตัว) ให้คนที่ฟังไม่ต่อเนื่องได้ภาพรวมครบ
- เพิ่มประโยคพาคนฟังเข้าไปในฉาก 3 จุด (ข้างฝ่ายตั้งรับตอนกลางคืน · บนกำแพงตอนปืนยิง · บนกำแพงทะเลตอนเช้าที่เรือบุกเข้ามา)
- ตัด "If you enjoyed this video, please like and subscribe" ออก แทนด้วยใบ้ตอนถัดไปที่เป็นคำถาม + CTA ที่ผูกกับซีรีส์ และปิดด้วยคำประจำช่อง "Until next time, keep looking back."

**ข้อสังเกต:** การเพิ่มประโยคพูดกับผู้ชมใน hook ทำให้คะแนนรอบ 1 ลดจาก 94.3 เป็น 88.7 เพราะคำถามแรกถูกดันไปที่ 25 วินาที จึงย้ายประโยคนั้นไปหลังคำถาม คะแนนกลับมาที่ 92.0 พบบั๊กตัวตรวจใบ้ตอนถัดไป (อ่าน "How" ตัวพิมพ์ใหญ่ไม่ออก) แก้แล้ว ส่วนตัววัด "ชื่อที่ปูทาง" ผ่านตั้งแต่ v0 แปลว่าหยาบเกินไป ควรเปลี่ยนเป็นการติดป้าย setup/payoff ด้วยมือในรอบต่อไป

**กฎที่ได้:** ตอนจบต้องตอบคำถามใน hook ด้วยคำเดิม · สรุปสาเหตุใน 3 ประโยค · ห้ามจบด้วย CTA ทั่วไป · ใบ้ตอนถัดไปเป็นคำถามเจาะจง · คำปิดประจำช่องเหมือนกันทุกคลิป · พูดกับ "you" 1–4 ครั้งต่อนาที ในฉากที่พาเข้าไปยืนในเหตุการณ์

## แนวทางฉบับสุดท้าย

เรียงตามลำดับในคลิป ตัวเลขในวงเล็บคือเกณฑ์ที่ score.py ตรวจ

| ส่วน | กฎ | เกณฑ์ตรวจ |
| --- | --- | --- |
| Title + thumbnail | คำหลักต้องได้ยินในบทช่วงแรก | ครบทุกคำใน 30 วินาที |
| Hook | เปิดกลางเหตุการณ์ด้วยวันเวลา/สถานที่ บอกตอนจบ แล้วถาม how/why | ประโยคแรก ≤14 คำ · คำถามแรก ≤12–20 วินาที |
| Promise | บรรทัดเดียว ปริศนาไม่เกิน 2 ห้ามไล่สารบัญ ห้าม "in this video" | Hook+Promise 20–40 วินาที |
| ทุกบท | 1 ประโยค 1 ความคิด 1 ตัวเลข active voice ประโยคยาวตามด้วยสั้น | เฉลี่ย 8–16 คำ · เกิน 20 คำ ≤10% · Flesch ≥65 |
| ระหว่างจังหวะ | but / so / still แทน and then | and then = 0 · ≥2 ครั้งต่อนาที |
| เนื้อเรื่อง | อุปสรรคจริงทุกบท ตัวละครมีชื่อและมีสิ่งที่ต้องการ | ≥3 คน · คำถาม/คำใบ้ทุก ≤90 วินาที |
| ท้ายบท | ปิด loop เก่า เปิด loop ใหม่ในลมหายใจเดียวกัน | ทุกส่วนก่อนจุดพีค |
| เสียง | เพลงบรรเลง เปลี่ยนตามบท J/L-cut ทุกรอยต่อ เว้นหลังข้อเท็จจริงใหญ่ | เพลง −18 ถึง −24 dB · −14 LUFS · เว้น ≤3 วินาที |
| จุดพีค | เงียบเพลงก่อนเฉลย พาคนฟังไปยืนในฉาก ("Picture yourself…") | 60–85% ของคลิป |
| Close | ตอบคำถาม hook ด้วยคำเดิม สรุปสาเหตุ 3 ประโยค ใบ้ตอนต่อไปเป็นคำถาม ปิดด้วยคำประจำช่อง | CTA ทั่วไป = 0 |
| ทั้งคลิป | พูดกับ "you" ในฉากสำคัญ ปิดจอแล้วยังเข้าใจครบ ผู้บรรยายคนเดิมทุกตอน | you 1–4 ครั้ง/นาที · คำที่ต้องดูจอ = 0 |

**ข้อยกเว้นที่ตั้งใจ:** คู่ตัวเลขที่เป็นหัวใจของ hook (พันปี กับ 53 วัน) อยู่ในประโยคเดียวกันได้ ทั้งตอนเปิดและตอน callback ส่วนตัวเลขอื่นแยกประโยค

**สำหรับช่องไทย:** กฎโครงเรื่อง เสียง และตอนจบใช้ได้เหมือนกัน แต่เกณฑ์ความยาวประโยคและ Flesch ใช้กับภาษาอังกฤษเท่านั้น ช่องไทยต้องตั้งเกณฑ์ใหม่เป็น "วรรคหายใจ" (เช่น ไม่เกิน 3–4 วินาทีต่อวรรค) และตัดคำด้วย PyThaiNLP ก่อนวัด

## บทตัวอย่างฉบับสุดท้าย

v5 ตอน Constantinople (ราว 6.6 นาที) บรรทัดใน \[ \] คือคำสั่งงานภาพและเสียง ข้อเท็จจริงทุกข้อต้องตรวจกับแหล่งข้อมูลอีกรอบก่อนอัดเสียง

```text
TITLE: How 53 Days Broke a Thousand-Year Wall
THUMB: 53 DAYS
SIGNOFF: Until next time, keep looking back.

## HOOK
[MIX: voice leads; music -20 dB under voice, auto-duck; whole mix -14 LUFS, true peak -1 dBTP]
[MUSIC: low instrumental drone, no vocals]
[VISUAL: torchlight along the land walls at night; drone slowly descends]
[SFX: distant drums, then sudden silence]
It is half past one in the morning, on 29 May 1453.
Seven thousand defenders stand on the walls of Constantinople, waiting in the dark.
By sunrise, walls that have stood for a thousand years will fall.
[PAUSE 1.5]
How did a young sultan break a thousand-year wall in just 53 days?
If you stood beside the defenders tonight, you would hear drums out in the dark.
No army had ever broken these walls by force. But below them waits an army many times larger.

## PROMISE
[J-CUT: creak of a ship's hull starts under the last hook shot]
It came down to a cannon that nobody else would pay for, and a fleet that sailed over a hill.
Let's go back to the city at its height.

## CONTEXT
[SOUND BRIDGE: harbour gulls and bells fade in 1s before the cut]
[MUSIC: warm instrumental theme, strings and oud, no vocals]
Constantinople was a Roman city. The emperor Constantine the Great made it his new capital in 330 AD.
In the centuries that followed, the western half of the Roman Empire collapsed. But the eastern half survived.
Historians call it the Byzantine Empire. It lasted another thousand years.
Water protected the city on three sides. On the fourth side stood the Theodosian Walls.
They were not one wall, but three layers. First came a moat. Behind it, an outer wall. Behind that, a taller inner wall.
Together, they ran for almost six kilometres, from the Sea of Marmara to the Golden Horn.
But by 1453, the empire had shrunk to little more than the city itself.
The city was a shadow of its old self. Perhaps fifty thousand people still lived inside the walls.
Outside, the Ottoman Turks had spread across Anatolia and the Balkans. They now surrounded the city on almost every side.
In 1451, a new sultan took the throne. His name was Mehmed. He was eighteen.
[PAUSE 1]
Few in the West took him seriously. They would soon regret it.
Mehmed wanted one prize above all others. Constantinople.
In 1452, he built a fortress on the European shore of the Bosphorus. From there, his guns could stop any ship.
Inside the city, Constantine the Eleventh begged the West for help. Very little came.
But Mehmed had a problem too. No cannon in his army could break walls like these.

## CHAPTER 1
[J-CUT: foundry hammering starts under the last context shot]
[MUSIC: percussive instrumental, slow build, no vocals]
So when a Hungarian engineer named Orban came looking for work, Mehmed listened.
Orban cast cannons. Big ones, in bronze.
He had gone to the Byzantine emperor first. But Constantine could not afford his price.
So Orban went to Mehmed instead. Mehmed paid him far more than he asked, and gave him everything he needed.
Orban built a monster. The cannon was around eight metres long.
It could throw a stone ball weighing several hundred kilograms for more than a mile.
Moving it took sixty oxen and hundreds of men.
[SFX: oxen, ropes, wheels groaning]
Mehmed would soon learn that size was not everything.
[MUSIC: out for 2s]
[SFX: first cannon shot, long echo]
On 6 April 1453, the siege began.
The guns fired every day, for weeks.
Imagine you are on the wall when the great cannon fires. You feel the shot in your chest before you hear it.
But the great cannon could only fire a few times a day. It had to cool down between shots.
Still, every hit tore open part of the outer wall.
So every night, the defenders came out to repair it. They packed the gaps with timber, earth and barrels.
On 18 April, Mehmed sent his men at the broken wall. The defenders threw them back.
The walls were cracking. But they had not fallen. And as long as the harbour stayed open to friendly ships, the city could hold on.
[PAUSE 1]
Which leaves the real question of this siege. How do you beat a city you cannot cut off?

## TURNING POINT
[L-CUT: the question's echo carries over the first harbour shot]
[MUSIC: tense instrumental pulse, no vocals]
Across the mouth of the Golden Horn, the Byzantines had stretched a huge chain. It kept the Ottoman fleet out.
On 20 April, something went wrong for Mehmed. Four Christian ships fought their way through his navy and reached the harbour.
Mehmed watched from the shore. He was furious.
So he chose a plan that sounded impossible.
[PAUSE 1]
Behind the Genoese town of Galata, his men laid a road of greased logs.
On 22 April, they dragged their ships over the hill.
[MUSIC: out]
[SFX: wood scraping on logs, then silence]
Picture yourself on the sea wall that morning. You look down at water that was safe yesterday.
Around seventy Ottoman ships are floating inside the harbour.
Now the city had to guard its sea walls too. Its seven thousand defenders were stretched even thinner.
Even so, the walls held for another month. So what finally broke them?
By late May, Mehmed's own grand vizier, Halil, urged him to give up.
But Mehmed refused. Instead, he ordered one final assault.
[MUSIC: drums only, instrumental]
It began early on 29 May.
The Genoese commander, Giovanni Giustiniani, took a serious wound. His men carried him away from the walls.
The defenders saw him go. Panic spread.
Ottoman soldiers broke through.
Constantine the Eleventh died in the fighting. No one ever identified his body.
[PAUSE 2]

## CLOSE
[J-CUT: dawn call and wind start under the final battle shot]
[MUSIC: main theme returns, soft, instrumental]
So that is how a thousand-year wall fell in 53 days.
It did not fall to one cannon, or to one clever trick.
The cannon cracked the walls. The ships over the hill stretched the defenders thin. And when Giustiniani left the wall, their hope left with him.
Behind all of it stood a young sultan who would not give up.
The fall of Constantinople ended the Byzantine Empire. The city became the new Ottoman capital. In time, the world would know it as Istanbul.
Many Greek scholars fled west to Italy. They carried books and ideas that helped feed the Renaissance.
[PAUSE 1]
You can still walk along those walls today. Long stretches of them still stand, scarred by centuries of war.
Next time, we follow Mehmed into the broken city. How did Mehmed turn it into the capital of an empire?
That episode is part of this series, so subscribe if you want to walk the walls with me again.
Until next time, keep looking back.
```

## ข้อจำกัดและวิธีวัดจริงบน YouTube

**ข้อจำกัดของการทดลองนี้**

- **ตัววัดเป็นตัวแทน ไม่ใช่คนดูจริง:** ทุกตัววัดตรวจว่าบททำตามกฎจากงานวิจัยหรือไม่ ไม่ได้พิสูจน์ว่าคนจะดูนานขึ้น
- **ผมออกแบบตัววัดและแก้บทเอง:** จึงมีความเสี่ยงที่จะแก้เพื่อให้ผ่านตัววัดมากกว่าเพื่อคนฟัง อย่างรอบ 4 ที่ได้ 100 เพราะตรวจแค่ว่ามีแผนเสียงครบ และตัววัด "ชื่อที่ปูทาง" ที่ผ่านตั้งแต่ v0
- **เกณฑ์บางข้อมาจากแนวปฏิบัติ ไม่ใช่งานวิจัย:** เช่น ระดับเพลง −18 ถึง −24 dB และ "คำใบ้ทุก 2–3 นาที" มาจากคู่มือครีเอเตอร์ ผมตั้ง ≤90 วินาทีเองเพราะบททดสอบสั้นกว่าคลิปจริง
- **ทดสอบกับบทเดียว ภาษาอังกฤษเท่านั้น:** ยังไม่ได้พิสูจน์กับตอนอื่นหรือบทไทย และตัวเลขประวัติศาสตร์ในบท (ขนาดปืน จำนวนเรือ จำนวนทหาร) เป็นค่าประมาณที่ผมเขียนจากความรู้ ต้องตรวจกับแหล่งข้อมูลก่อนอัด

**วิธีวัดจริงหลังลงคลิป**

| สิ่งที่วัด | ดูที่ | เกณฑ์เบื้องต้น |
| --- | --- | --- |
| Hook ได้ผลไหม | Studio → Audience retention → Intro | เสียคนไม่เกิน 40% ใน 30 วินาทีแรก |
| กลางคลิปหลุดตรงไหน | Key moments: dips และ top moments | ไม่มีหน้าผากตรงรอยต่อบท |
| ดูจนจบแค่ไหน | Average percentage viewed | คลิปยาว 35–50% ถือว่าดี |
| คนกลับมาดูซ้ำ | Returning viewers · การดูต่อผ่าน end screen | เทียบตอนต่อตอนในซีรีส์ |

**การทดสอบก่อนลงคลิป (แนะนำ):** อัดเสียง v0 กับ v5 แล้วให้คน 5–10 คนฟังแบบปิดจอขณะทำงานอื่น ให้จดวินาทีที่เริ่มใจลอย แล้วถาม 3 ข้อหลังฟังจบ (ใครสร้างปืน เรือเข้าอ่าวได้อย่างไร ทำไมเมืองแตก) นี่คือการวัดคนจริงที่ถูกที่สุดก่อนมียอดวิว

แหล่งเกณฑ์: [YouTube Help](https://support.google.com/youtube/answer/1715160?hl=en) · [Opus](https://www.opus.pro/blog/youtube-retention-graphs-explained) · [Uppbeat](https://fastly-f.uppbeat.io/blog/youtube-growth/youtube-analytics/youtube-audience-retention)

## แหล่งอ้างอิง

ลิงก์ของแต่ละรอบอยู่ในหัวข้อ "ค้นคว้า" ของรอบนั้น งานวิจัยหลักที่ใช้ตั้งกฎ:

- Leavitt & Christenfeld (2011) Spoilers don't spoil stories · [UC](https://www.universityofcalifornia.edu/news/spoiler-alert-spoilers-make-you-enjoy-stories-more) · [งานทำซ้ำ](https://core.ac.uk/download/72840983.pdf)
- Gerrig: anomalous suspense · [Stony Brook](https://researchconnect.stonybrook.edu/en/publications/suspense-in-the-absence-of-uncertainty/)
- Parker & Stone: but/therefore · [Cheat Sheet](https://www.cheatsheet.com/entertainment/south-park-trey-parker-and-matt-stone-1-rule.html/)
- คู่มือเขียนข่าววิทยุ/ทีวี · [The News Manual](https://thenewsmanual.net/Manuals%20Volume%202/volume2_48.htm) · [Human Kinetics](https://canada.humankinetics.com/blogs/excerpt/tips-for-writing-for-broadcast)
- ความเร็วพูดกับการฟังเข้าใจ · [McMaster](https://experts.mcmaster.ca/scholarly-works/2127220) · การเว้นจังหวะ [J-STAGE](https://www.jstage.jst.go.jp/article/arele/27/0/27_97/_article/-char/en)
- เพลงมีเนื้อกับการจำ · [PMC 2023](https://pmc.ncbi.nlm.nih.gov/articles/PMC10162369/)
- Kahneman: peak-end rule · [Wikipedia](https://en.wikipedia.org/wiki/Peak%E2%80%93end_rule)
- Hartmann & Goldhoorn (2011) direct address · [VU](https://typeset.io/pdf/horton-and-wohl-revisited-exploring-viewers-experience-of-2x3qk052xt.pdf) · Atad & Cohen (2024) [Haifa](https://cris.haifa.ac.il/en/publications/look-me-in-the-eyes-how-direct-address-affects-viewers-experience/)
- Russell & Levy (2012) reconsumption · [Ready Steady Cut](https://readysteadycut.com/2022/09/26/the-psychology-behind-rewatching)

ไฟล์ประกอบ: score.py (ตัววัด 36 ข้อ) และบท v0–v5 ส่งในแชท

## ตัววัดบทภาษาไทย (P1.5, 22 พ.ย. 2026)

`tools/score_th.py` ใช้ 5 รอบเดิม แต่วัดแบบภาษาไทย (score.py ตรวจว่าบทเป็นภาษาไทยแล้วเรียกให้เอง)

- **เวลา:** นับพยางค์ด้วย PyThaiNLP (อ่านตัวเลขเป็นคำ เช่น 1453 = 7 พยางค์) ที่ 4.0 พยางค์/วินาที ตั้งให้บท v5 ฉบับไทยยาวพอๆ กับฉบับอังกฤษ (6.1 vs 6.6 นาที) ต้องเทียบกับเสียงพากย์ไทยจริงตอนแรกแล้วปรับ
- **ประโยค = 1 บรรทัด, ช่วงหายใจ = วลีที่คั่นด้วยเว้นวรรค:** แทนความยาวประโยคเป็นคำและ Flesch ช่วงหายใจเฉลี่ย 1–3 วินาที เกิน 4 วินาทีได้ไม่เกิน 10%
- **คำเฉพาะภาษาไทย:** คำเปิดต้องห้าม (สวัสดี, ในคลิปนี้, วันนี้เราจะ), คำเชื่อม แต่/ดังนั้น/ถึงอย่างนั้น แทน แล้วก็/จากนั้น/ต่อมา, passive ถูก/โดน/ได้รับการ, อนุประโยคซ้อน ซึ่ง/โดยที่, เรียก "คุณ" 1–4 ครั้งต่อนาที
- **ชื่อคน/สถานที่:** ภาษาไทยไม่มีตัวพิมพ์ใหญ่ บทไทยจึงต้องมีบรรทัด `CAST:` และ `PLACES:`

ผลกับบทแปล v0/v5 (แปลตรงตามต้นฉบับ ข้อเสียของ v0 ยังอยู่ครบ): v0 = 28.7, v5 = 99.0 (ฉบับอังกฤษ 31.0 / 97.3)
