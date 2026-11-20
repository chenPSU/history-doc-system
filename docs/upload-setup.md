# ตั้งค่าอัปโหลดอัตโนมัติขึ้น YouTube

ระบบอัปโหลดผ่าน YouTube Data API v3 ด้วยบัญชีของคุณเอง (OAuth) ทำครั้งเดียวต่อช่อง ใช้เวลาราว 30 นาที ไม่รวมเวลารอ Google ตรวจโปรเจกต์

## ข้อจำกัดจาก YouTube ที่ต้องรู้ก่อน

1. **ต้องผ่านการตรวจโปรเจกต์ API ก่อน วิดีโอถึงจะเป็นสาธารณะได้**
   วิดีโอที่อัปผ่าน `videos.insert` จากโปรเจกต์ที่สร้างหลัง 28 ก.ค. 2020 และยังไม่ผ่านการตรวจ จะถูกล็อกเป็นส่วนตัว (private) และมีรายงานว่าเปลี่ยนเป็นสาธารณะภายหลังไม่ได้
   ระบบจึงตั้งไว้ว่า ตราบใดที่ `audit_passed: false` จะอัปได้เฉพาะวิดีโอทดสอบ (`test_upload: true` ใน brief.yaml) ส่วนตอนจริงให้อัปเองใน YouTube Studio จากแพ็กเกจที่ระบบเตรียมให้
2. **โควตา:** โปรเจกต์ใหม่อัปได้ 100 วิดีโอต่อวัน (นับแยกจากการเรียก API อื่น) เกินพอสำหรับ 4 ตอนต่อสัปดาห์
3. **โทเค็นหมดอายุ 7 วันถ้าแอปยังเป็นโหมด Testing:** ต้องกด Publish app ให้เป็น In production (ขั้นที่ 3)
4. **แจ้ง AI:** ถ้าตอนไหนมีภาพ AI ที่ดูเหมือนจริง ให้ตั้ง `altered_or_synthetic_disclosure: true` ใน metadata.yaml ระบบจะส่ง `containsSyntheticMedia` ให้เอง

## ขั้นตอน

### 1. สร้างโปรเจกต์
ไปที่ console.cloud.google.com → สร้างโปรเจกต์ใหม่ เช่น `history-doc-uploader` ใช้บัญชี Google ที่เป็นเจ้าของทั้งสองช่อง

### 2. เปิด API
APIs & Services → Library → ค้น **YouTube Data API v3** → Enable

### 3. ตั้งหน้าขอสิทธิ์ (OAuth consent screen)
- User type: **External**
- ใส่ชื่อแอปและอีเมลของคุณ
- Scopes: เพิ่ม `.../auth/youtube.upload` และ `.../auth/youtube.force-ssl`
- Test users: ใส่อีเมลของคุณ
- กด **Publish app** ให้สถานะเป็น **In production** เพื่อไม่ให้โทเค็นหมดอายุทุก 7 วัน
  ตอนล็อกอินครั้งแรก Google อาจขึ้นว่า "แอปนี้ยังไม่ได้รับการยืนยัน" กด Advanced → ไปต่อได้ เพราะเป็นแอปของคุณเอง
  ถ้า Google บังคับให้ยืนยันแอปก่อน ให้ส่งยืนยันตามขั้นตอน หรือใช้โหมด Testing ไปก่อน แล้วรัน `auth_youtube.py` ใหม่ทุกสัปดาห์

### 4. สร้าง OAuth client
Credentials → Create credentials → OAuth client ID → Application type: **Desktop app** → ดาวน์โหลด JSON → บันทึกเป็น `secrets/client_secret.json`

### 5. ล็อกอินทีละช่อง (ทำบนเครื่องคุณ เพราะจะเปิดเบราว์เซอร์)
```
pip install -r requirements.txt
python tools/auth_youtube.py --lang en --write-channel-id
python tools/auth_youtube.py --lang th --write-channel-id
```
ตอนเลือกบัญชี ให้เลือก**ช่องของภาษานั้น** (Brand Account) สคริปต์จะพิมพ์ชื่อช่องให้ตรวจ ถ้าผิดช่องให้รันใหม่
ทุกครั้งก่อนอัป ระบบจะเช็กว่าโทเค็นตรงกับ `channel_id` ใน `config/upload_policy.yaml` ถ้าไม่ตรงจะไม่อัป จึงไม่มีทางที่ตอนไทยจะไปขึ้นช่องอังกฤษ

### 6. ทดสอบด้วยวิดีโอสั้น
สร้างตอนทดสอบ (คลิป 10 วินาที) ใส่ `test_upload: true` ใน brief.yaml แล้วรัน:
```
python tools/upload.py episodes/<ตอนทดสอบ>          # ดูก่อนว่าจะส่งอะไร
python tools/upload.py episodes/<ตอนทดสอบ> --go     # อัปจริง (จะเป็น private)
```
เช็กใน Studio ว่าชื่อ คำอธิบาย ภาพปก ซับไตเติล เพลย์ลิสต์ และป้าย AI ขึ้นถูกต้อง แล้วลบวิดีโอทดสอบทิ้ง

### 7. ขอผ่านการตรวจ (Audit)
ส่งแบบฟอร์ม **YouTube API Services – Audit and Quota Extension Form** (ลิงก์อยู่ในหน้า Quota and Compliance Audits ของ Google)
บอกว่าเป็นเครื่องมือภายในสำหรับอัปโหลดคอนเทนต์ต้นฉบับของช่องตัวเอง 2 ช่อง แนบภาพหน้าจอของขั้นตอนอัป
ระหว่างรอ (อาจใช้หลายสัปดาห์และไม่รับประกันว่าจะผ่าน) ให้อัปตอนจริงเองใน Studio โดยคัดลอกค่าจาก metadata.yaml
**เมื่อผ่านแล้ว** แก้ `audit_passed: true` และเลือกโหมดใน `config/upload_policy.yaml`

### 8. เลือกโหมด
| โหมด | เกิดอะไรขึ้น | เหมาะกับ |
|---|---|---|
| `private` | อัปแล้วเก็บเป็นส่วนตัว คุณกดเผยแพร่เองใน Studio | ช่วงแรก |
| `scheduled` | อัปเป็นส่วนตัว แล้วตั้งเวลาเผยแพร่ช่องถัดไป (อย่างน้อย 24 ชม. หลังอัป ให้มีเวลาตรวจหรือยกเลิก) | **แนะนำ** เมื่อผ่าน audit |
| `public` | เผยแพร่ทันที | ไม่แนะนำ |

เวลาเผยแพร่ตั้งไว้ใน `publish_slots_utc`: อังกฤษ อังคาร/ศุกร์ 22:00 UTC (ราว 5 โมงเย็นฝั่งตะวันออกของสหรัฐฯ), ไทย พุธ/เสาร์ 12:00 UTC (1 ทุ่มเวลาไทย)

### 9. การอนุมัติ
ถ้า `require_owner_approval: true` แต่ละตอนต้องมีไฟล์ `approved.yaml`:
```yaml
approved_by: <ชื่อคุณ>
approved_at: 2026-12-12
```
บอก Claude Code ว่า "อนุมัติตอน 2026-12-14-en-constantinople" แล้วมันจะสร้างไฟล์ให้ (สร้างเฉพาะตอนที่คุณสั่งเท่านั้น)
ถ้าต้องการอัตโนมัติเต็มรูปแบบ ตั้ง `require_owner_approval: false` ระบบจะยังตรวจคะแนนบท preflight และลิขสิทธิ์ภาพก่อนอัปทุกครั้ง และโหมด `scheduled` ยังให้เวลาคุณ 24 ชั่วโมงก่อนเผยแพร่

### 10. ตั้งเวลาให้รันเอง
บนเครื่องที่เปิดทิ้งไว้ (Mac/Linux ใช้ cron):
```
0 9 * * * cd /path/to/history-doc-system && /usr/bin/python3 tools/upload.py --queue --go >> upload.log 2>&1
```
Windows ใช้ Task Scheduler รันคำสั่งเดียวกัน ทุกเช้าระบบจะหาตอนที่ผ่านทุกด่าน แล้วอัปตามนโยบาย ส่วนตอนที่ไม่ผ่านจะถูกข้ามพร้อมเหตุผลใน log
