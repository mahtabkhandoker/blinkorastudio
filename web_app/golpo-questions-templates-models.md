# Golpo: Questions, Templates and Models

One reference for the build: what we ask the seller, the prompts we send, and the models we send them to.

Prices were checked between 18 October and 7 November 2026, and every price has a source in §3.13. Prices in this market change monthly, so recheck them in each provider's console before setting a customer price. Where this file estimates or derives a figure, it says so.

**Codes used throughout**

| Prefix | Meaning | Example |
|---|---|---|
| `G1`–`G5` | Product group | `G4` Flowing |
| `S1`–`S4` | Service scenario | `S3` Person at work |
| `B00`–`B12` | Business type | `B09` Honey, ghee, hair oil |
| `-A` `-B` `-C` | Shot: main, close-up, wide | `G4-B` is the Flowing close-up |
| `F` `Q` `GQ` `SQ` `P` `C` `R` | Question families (see §1.2) | `GQ5` wet or dry |

---

# Part 1: The questions

## 1.1 Five kinds of question

Ordered from the most effort for the seller to the least. Each phase moves questions down this table.

| Kind | What he does | Example | Effort |
|---|---|---|---|
| **Upload** | Sends a file | লোগো পাঠান | Highest. Always offer `এখন নেই` |
| **Type** | Writes an answer | এটা কী, এক লাইনে? | High |
| **Choose** | Picks an option | ভেজা · শুকনো | One tap (a number in P0) |
| **Confirm** | Accepts our guess | এটা কি কাঁচা আম? হ্যাঁ · বদলাব | One tap |
| **Detect** | Nothing | We spot a face or blur | None, never asked |

**Rules for every question**

- One question per message or screen, never a form of ten fields.
- Two to four options, one already selected, plus `নিজে লিখব` for typing instead.
- Every question has a default, so a seller who skips still gets an ad.
- Ask about his product, never about video. Ask "কাপড়টা পাতলা নাকি ভারী?", never "camera movement?"
- Never ask what the photo already shows.
- Taps first, typing later, uploads last.
- At most one clarifying question when something is unclear, then use the default.

---

## 1.2 The full question register

`Phase` is when the question first appears. `Goes to` says where the answer is used:

- **prompt**: into the video prompt
- **avoid**: into the negative prompt
- **post**: added in editing, never sent to the video model
- **profile**: saved for next time
- **route**: decides the group or scenario
- **log**: kept in the order record

### F · Settings (asked before anything else)

| Code | Bengali | Options | Kind | Goes to | Phase |
|---|---|---|---|---|---|
| F1 | কোথায় দেবেন? | `রিল / টিকটক` (9:16) · `পোস্ট` (1:1) · `দুইটাই (+৳___)` | Choose | profile, route | P0 |

On the website this is a toggle above the upload, not a question. Set the add-on price after testing the 9:16-to-square crop (§3.4).

### Q · Core questions (every order)

| Code | Bengali | Options / format | Kind | Goes to | Phase |
|---|---|---|---|---|---|
| Q1 | কী বিক্রি করেন? | List: `পোশাক` · `খাবার` · `প্রসাধনী` · `গয়না ও ঘড়ি` · `মোবাইল ও ইলেকট্রনিক্স` · `সার্ভিস` · `অন্য কিছু` | Choose | route | P0 |
| Q2 | এটা কী, কী দিয়ে তৈরি? এক লাইনে লিখুন | Free text, e.g. "লাল সুতির শাড়ি". From P3 the photo pre-fills it: `লাল সুতির শাড়ি` · `বদলাব` | Type → Confirm | prompt | P0 |
| Q3 | ক্রেতার চোখ প্রথমে কোথায় পড়বে? | Per-group options (§1.2 note), plus `নিজে লিখব` | Choose | prompt (`DETAIL`) | P1 |
| Q4 | ভিডিওটা কেমন লাগবে? | `শান্ত ও দামি` · `সতেজ` · `ঘরোয়া` · `ঝকঝকে` | Choose | prompt (`MOOD`, `LIGHT`, `ACCENT`) | P1 |
| Q5 | পণ্যটা কোথায় থাকবে? | `ছবিরটাই` (default) · `সাদা স্টুডিও` · `কাঠের টেবিল` · `ঝুড়ি বা ট্রে` | Choose | prompt (`SURFACE`, `SETTING`) | P1 |
| Q6 | এমন কিছু আছে যা ভিডিওতে চান না? | `কিছু না` (default) · `মানুষ` · `হাত` · `পানি বা ধোঁয়া` | Choose, several allowed | avoid | P1 |

In P0, Q3–Q6 are not asked and the group defaults (§1.6) are used.

**Q1 → group.** `পোশাক` → G1, `প্রসাধনী` → G2, `গয়না ও ঘড়ি` → G3, `মোবাইল ও ইলেকট্রনিক্স` → G3, `খাবার` → Q1a, `সার্ভিস` → SQ1, `অন্য কিছু` → G2. G2 is the safest default.

**Q1a · কী ধরনের খাবার?** (only when Q1 = খাবার)
`তাজা — সবজি, ফল, মাছ` → G5 · `চাল, ডাল, মসলা, শুঁটকি` → G5 dry · `মধু, ঘি, তেল, দই` → G4 · `মিষ্টি, রান্না করা খাবার` → G2. Prepared food gets its own group only if orders show it is needed.

**Q4 sets three slots at once:**

| Button | `MOOD` | `LIGHT` | `ACCENT` |
|---|---|---|---|
| শান্ত ও দামি | calm and premium | warm low-angle side light, deep soft shadows | drifting dust motes |
| সতেজ | fresh and lively | bright clean daylight | light mist |
| ঘরোয়া | warm and unhurried | warm late-afternoon window light | faint steam |
| ঝকঝকে | crisp and confident | even diffused studio light | none |

**Q3 fallback options by group** (from P3, the options come from the photo instead):

| Group | Options |
|---|---|
| G1 Soft | পাড় · রঙ · নকশা · কাপড়ের বুনন |
| G2 Rigid | লেবেল · ঢাকনা · আকৃতি · গায়ের লেখা |
| G3 Reflective | পাথর · কারুকাজ · চকচকে ভাব · ডায়াল |
| G4 Flowing | ঘনত্ব · রঙ · ঢালার দৃশ্য · কৌটা |
| G5 Fresh | তাজা ভাব · রঙ · আকার · কাটা অংশ |

### GQ · Group questions (one per order, decided by the group)

These prevent the most expensive retries, so they are asked from P0.

| Code | Group | Bengali | Options | What the answer changes |
|---|---|---|---|---|
| GQ1 | G1 Soft | কাপড়টা পাতলা নাকি ভারী? | `পাতলা` · `মাঝারি` · `ভারী` | How much the fabric moves |
| GQ2 | G2 Rigid | লেবেলটা ছবিতে স্পষ্ট দেখা যাচ্ছে? | `হ্যাঁ` · `একটু ঝাপসা` | Whether we promise a readable label or crop tighter |
| GQ3 | G3 Reflective | গয়নাটা কিসের উপর রাখা? · ছবিতে আলোর ঝলক আছে? | `কাপড়` · `কাঠ` · `সাদা` / `হ্যাঁ` · `না` | Surface slot. If there is glare, we ask for a new photo before generating |
| GQ4 | G4 Flowing | ঢালা দেখাব, নাকি বন্ধ কৌটা? | `ঢালা` · `বন্ধ কৌটা` · `দুইটাই` (default) | **The shot plan** (see §2.4) |
| GQ5 | G5 Fresh | পণ্যটা ভেজা নাকি শুকনো? | `ভেজা / তাজা` · `শুকনো` | Droplets and mist, or none (the shutki rule) |

### SQ · Service questions (Q1 = সার্ভিস)

The photo of a service shows only the setting, so the offer, the price and the place must be asked.

| Code | Bengali | Options | Kind | Goes to | Phase |
|---|---|---|---|---|---|
| SQ1 | কী ধরনের সার্ভিস? | `দোকান বা জায়গা` (S1) · `কাজের ফলাফল` (S2) · `কাজ করছেন এমন ছবি` (S3) · `দামের তালিকা বা পোস্টার` (S4) | Choose | route | P0 |
| SQ2 | কী সার্ভিস দেন, এক লাইনে? | e.g. "চুল আর দাড়ি কাটা" | Type | post (text, voice) | P0 |
| SQ3 | দাম কত? | Free text, or `দাম লিখব না` | Type | post | P0 |
| SQ4 | কোথায় বসেন বা কোন এলাকায় সার্ভিস দেন? | Free text | Type | post | P0 |

**Scenario-specific questions**

| Code | Scenario | Bengali | Options |
|---|---|---|---|
| SQ5 | S1 Property | কয়টা রুম দেখাব? | `১` · `২` · `৩` · `৩+`. One clip per room, one photo per room |
| SQ6 | S1 Property | ভাড়া নাকি বিক্রি? | `ভাড়া` · `বিক্রি`. Goes to post only |
| SQ7 | S2 Result | আগের ছবি আছে? | `আছে` · `নেই`. A before-and-after is cut in editing, never generated |
| SQ8 | S3 Person | মুখ একটু বদলে যেতে পারে — মুখসহ বানাব, নাকি শুধু হাত আর কাজ? | `মুখসহ` · `শুধু কাজ` (recommended) |

### C · Confirmation (before any paid call)

| Code | Bengali | Options | Phase |
|---|---|---|---|
| C1 | ৩টি দৃশ্য বানাব: ১) … ২) … ৩) … ঠিক আছে? | `হ্যাঁ, বানান` · `বদলাতে চাই` | P0 |
| C2 | (if `বদলাতে চাই`) কোনটা বদলাবেন? | `১` · `২` · `৩` · `পণ্যের ধরন` | P0 |

The three lines come from the template's Bengali shot descriptions (§2.7). Never show the English prompt.

### P · Post-production questions (asked after C1, while the clips generate)

| Code | Bengali | Options | Kind | Goes to | Phase |
|---|---|---|---|---|---|
| P1 | দোকানের নাম ভিডিওতে যেভাবে চান, ঠিক সেভাবে লিখুন | Free text, then read back: "এভাবেই লিখব? **{name}**" `হ্যাঁ` · `ঠিক করব` | Type → Confirm | post, profile | P0 |
| P2 | লোগো থাকলে ছবিটা পাঠান | `পাঠাচ্ছি` · `লোগো নেই` | Upload | post, profile | P0 |
| P3 | ভিডিওতে এই নাম্বারটা দেব? {his WhatsApp number} | `হ্যাঁ` · `অন্য নাম্বার` | Confirm | post, profile | P0 |
| P4 | লোগো কোথায় বসাব? | `কোণায়` · `শেষে` · `দুই জায়গায়` (default: end card plus a small corner mark) | Choose | post, profile | P1 |
| P5 | ভিডিওতে দাম লিখব? | `হ্যাঁ` → "কত টাকা?" · `না` | Choose → Type | post | P1 |
| P6 | কণ্ঠ লাগবে? | `পুরুষ` · `নারী` · `লাগবে না` (default) | Choose | post, profile | P1 |
| P7 | গান কেমন হবে? | `নরম` · `উৎসবের` · `আধুনিক` · `লাগবে না` | Choose | post, profile | P1 |

Handling the logo (P2):

| What he sends | What we do |
|---|---|
| Clean logo, ideally transparent PNG | Corner mark plus end card |
| Screenshot with a white box | End card only; say so plainly |
| Blurry | Ask once: "ফাইল হিসেবে পাঠান" (WhatsApp compresses photos but not files) |
| Nothing | Set the shop name in clean type |

### R · After delivery

| Code | Bengali | Options | Goes to | Phase |
|---|---|---|---|---|
| R1 | ভিডিওটা কেমন হয়েছে? | `👍` · `👎` · `বদলাতে চাই` | log | P0 |
| R2 | (if `বদলাতে চাই`) কোন দৃশ্যটা? | `১` · `২` · `৩` · `পুরোটা` | log | P0 |

R1 is the only way to learn whether an ad was good rather than just generated. Ask it from the first order.

### Conditional messages (P3, triggered by the photo model)

| Trigger | Bengali | Options |
|---|---|---|
| Blurry or low resolution | ছবিটা একটু ঝাপসা। আসল ছবিটা দিতে পারবেন? | `পাঠাচ্ছি` · `এটা দিয়েই বানান` |
| Watermark or someone else's mark | ছবিতে অন্য জায়গার মার্ক আছে। নিজের তোলা ছবি দেবেন? | `পাঠাচ্ছি` · `নেই` (offer S4 poster tier) |
| Several products | ছবিতে কয়েকটা পণ্য আছে — কোনটার ভিডিও? | Buttons generated from the photo |
| Face present | ছবিতে মানুষ আছে। মুখ একটু বদলে যেতে পারে — নড়াচড়া কম রাখব, আর পাঠানোর আগে নিজেরা দেখব। | `ঠিক আছে` · `মুখ ছাড়া বানান` |
| Weak group guess | এটা কি {guess}? | `হ্যাঁ` · `না` → Q1 |

### Returning customer and later-phase questions

| Code | Bengali | Options | Phase |
|---|---|---|---|
| X1 | আগের মতোই — {mood}, {format}, নিচে {number}। বানাব? | `হ্যাঁ` · `বদলাতে চাই` | P1 (profiles) |
| X2 | শুধু এবারের জন্য? (when he changes something) | `শুধু এবার` · `সবসময়` | P1 |
| X3 | ঈদের অফার? | `হ্যাঁ` → offer text · `না` | P4 |
| X4 | HD ভিডিও চান? (+৳___) | `হ্যাঁ` · `না` | P4 |

### Never asked (the photo or the system answers these)

Product category when the photo is clear · wet or dry when obvious · packed or loose · whether a person is in frame · background clutter · image resolution · number of products · dominant colour · camera movement · lighting · lens.

---

## 1.3 Question order by phase

**P0 · Pilot** (website form, or WhatsApp numbered replies)

| Step | Question | Kind |
|---|---|---|
| Start | F1 format | Setting |
| Before the plan | Q1 trade (+ Q1a for food, or SQ1–SQ4 for services) | Choose / Type |
| | Q2 what it is | Type |
| | GQ group question | Choose |
| Plan | C1 | Confirm |
| While generating | P1 shop name (read back) · P2 logo · P3 number | Type · Upload · Confirm |
| After delivery | R1 | One tap |

A product order in P0 has three questions before the plan, three while it generates and one after. A service adds three typed answers (SQ2–SQ4).

**P1 and later, first order:** F1 → Q1 → Q2 → GQ → Q3 → Q4 → Q5 → Q6 → C1 → P1–P7 → R1.

**Returning seller:** photo → Q2 → Q3 → X1 → C1 → R1. Everything else comes from the profile.

---

## 1.4 How each channel shows the questions

| | Website | WhatsApp P0 | WhatsApp P1+ |
|---|---|---|---|
| Format | Form fields, one per screen | Saved replies with numbered options | Reply buttons (up to 3) or list menu (up to 10) |
| Choose questions | Tappable chips | "১, ২ বা ৩ লিখুন" | Buttons or list |
| Uploads | Upload field with `এখন নেই` | He sends the photo in the chat | Same |
| Typing | Text box | Free reply | Free reply |

**WhatsApp P0 message, exactly as sent (Q1):**

```
আপনি কী বিক্রি করেন? নম্বর লিখুন:
১ — পোশাক
২ — খাবার
৩ — প্রসাধনী
৪ — গয়না ও ঘড়ি
৫ — মোবাইল ও ইলেকট্রনিক্স
৬ — সার্ভিস
৭ — অন্য কিছু
```

**Which format each question needs in P1** (buttons allow 3 options, list menus 10):

| Buttons (≤3) | List menu (≤10) |
|---|---|
| F1, Q2 confirm, GQ1–GQ5, P1 read-back, P2, P3, P4, P6, C1, R1, X1, X2 | Q1, Q1a, Q3, Q4, Q5, Q6, SQ1, P7, C2, R2 |

Keep button titles under 20 characters and list rows under 24. Every Bengali option above fits.

---

## 1.5 Reading what he types

**Claims → motion.** Check the first message for these before asking Q3. They often answer it.

| He writes | Meaning | Sets |
|---|---|---|
| খাঁটি · khati | pure | thick slow pour (G4) |
| ঘন · ghono | thick | slow settling, surface close-up |
| তাজা · taja | fresh | droplets, light mist (G5 wet) |
| শুকনো · shukna | dry | G5 dry |
| চকচকে · chokchoke | shiny | moving highlight, product locked |
| নরম · norom | soft | gentle ripple, shallow focus |
| হাতের কাজ | handmade | macro on stitching or cut edge |
| গরম · gorom | hot | rising steam |
| সুন্দর · sundor | beautiful | no information, so ask Q3 |

**Free text → slot values (P2):**

| He writes | Maps to |
|---|---|
| "simple rakhen", "সাদামাটা" | Q4 = ঝকঝকে, Q5 = সাদা স্টুডিও |
| "rajkiyo", "premium", "দামি" | Q4 = শান্ত ও দামি |
| "dhoa uthbe", "gorom gorom" | `ACCENT` = faint steam |
| "beshi nara chara na" | one step less motion |
| "mist lagbe na" | `ACCENT` = none; add mist to avoid |
| "reel er jonno" | F1 = রিল |

If the meaning isn't clear, ask once with buttons, then use the default. Never loop. Log every typed answer: the P0 and P1 answers are the test set for the P2 text model.

**Never send to the video model:** price, shop name, phone number, guarantees ("১০০% অরিজিনাল"), delivery terms, or any Bengali text. All of it goes to post-production.

---

## 1.6 Defaults (when he skips)

| Slot | G1 Soft | G2 Rigid | G3 Reflective | G4 Flowing | G5 Fresh |
|---|---|---|---|---|---|
| `DETAIL` | the woven texture and border | the front of the label | the surface and finish | the thick surface | the surface texture |
| `SURFACE` | a plain surface | a dark wooden table | a dark cloth | a dark wooden table | a woven bamboo tray |
| `SETTING` | a soft neutral backdrop | a warm simple interior | an uncluttered dark background | a warm simple interior | a simple market setting |
| `MOOD` | calm and premium | calm and premium | calm and premium | warm and unhurried | fresh and lively |
| `LIGHT` | warm side light | even studio light | soft directional light | warm window light | bright daylight |
| `ACCENT` | drifting dust motes | drifting dust motes | none | none | light mist (none if dry) |

---

## 1.7 Worked examples

**Mango seller, P0 (product, G5 dry).** Two typed answers in total.

| Code | We ask | He answers | It sets |
|---|---|---|---|
| F1 | রিল না পোস্ট? | রিল | 9:16 |
| Q1 | কী বিক্রি করেন? | খাবার | → Q1a |
| Q1a | কী ধরনের খাবার? | তাজা | G5 |
| Q2 | এটা কী, এক লাইনে? | কাঁচা আম | `PRODUCT` |
| GQ5 | ভেজা নাকি শুকনো? | শুকনো | dry variant |
| C1 | ৩টি দৃশ্য বানাব — ঠিক আছে? | হ্যাঁ | generation starts |
| P1 | দোকানের নাম? | আম বাজার | end card |
| P2 | লোগো? | লোগো নেই | name in type |
| P3 | এই নাম্বারটা দেব? | হ্যাঁ | number on screen |
| R1 | কেমন হয়েছে? | 👍 | log |

**Street barber, P0 (service, S3).**

| Code | We ask | He answers | It sets |
|---|---|---|---|
| — | (watermark found) নিজের ছবি দেবেন? | পাঠাচ্ছি | clean photo first |
| Q1 | কী বিক্রি করেন? | সার্ভিস | → SQ1 |
| SQ1 | কী ধরনের সার্ভিস? | কাজ করছেন এমন ছবি | S3 |
| SQ2 | কী সার্ভিস দেন? | চুল আর দাড়ি | post text |
| SQ8 | মুখসহ, নাকি শুধু কাজ? | মুখসহ | three tries on the face shot, then a still push-in |
| SQ3 | দাম কত? | চুল কাটা ১০০ টাকা | post text |
| SQ4 | কোথায় বসেন? | মিরপুর ১০ | post text |
| C1 | ৩টি দৃশ্য — ঠিক আছে? | হ্যাঁ | generation starts |
| P1 / P3 | নাম · নাম্বার | রহিম ভাই · হ্যাঁ | end card |
| R1 | কেমন হয়েছে? | 👍 | log |

---

# Part 2: The templates

## 2.1 Rules for every prompt

1. **Describe motion, not the product.** The photo already carries shape, colour and label, and re-describing them makes the model re-invent them.
2. **One motion and one camera move.** Two motions in one prompt is the main cause of failed clips.
3. **An anchor phrase**: "stays unchanged", "label unchanged" or "shape fixed".
4. **45 to 70 words.** Past roughly 70, models start dropping instructions.
5. **No text, letters or logos.** Overlays are added in editing.
6. **Store the parts, not the sentence.** Keep the slots and shot type as separate fields and build the sentence at generation time, so a model change means editing one assembler rather than every template.

## 2.2 Slots

| Slot | Filled by | Example |
|---|---|---|
| `{{PRODUCT}}` | Q2 | red cotton saree |
| `{{MATERIAL}}` | Q2 or group default | soft handloom cotton |
| `{{DETAIL}}` | Q3, claim or default | the gold zari border |
| `{{SURFACE}}` / `{{SETTING}}` | Q5 or default | a dark wooden table |
| `{{MOOD}}` `{{LIGHT}}` `{{ACCENT}}` | Q4 or default | calm and premium · warm side light · drifting dust motes |
| `{{MOTION_LEVEL}}` | GQ1 (Soft only) | gently / noticeably / slowly, holding its weight |

## 2.3 Product templates (5 groups × 3 shots)

### G1 · Soft (cloth ripples)

**G1-A Main**
```
The {{PRODUCT}} in the image stays centred, unchanged and in sharp focus. A breeze moves {{MOTION_LEVEL}} through the {{MATERIAL}}, making the fabric ripple and settle. The camera pushes in slowly from a medium shot. {{LIGHT}} sweeps across the surface, and {{DETAIL}} catches the light as it moves. {{MOOD}} pace. Shallow depth of field, natural colour, no cuts.
```
**G1-B Close-up**
```
Extreme close-up on {{DETAIL}} of the {{PRODUCT}}. The garment itself does not move or change. The camera glides slowly from right to left across the surface while soft light travels over the {{MATERIAL}}, revealing weave and thread texture. {{LIGHT}}. Slow, deliberate pace. Macro lens look, fine texture, no cuts.
```
**G1-C Wide**
```
The {{PRODUCT}} hangs still against {{SETTING}}, slightly left of frame with empty space on the right. Only the lower hem sways very slightly. The camera slowly pulls back to a wide shot. {{LIGHT}} with soft falling shadows. {{MOOD}} pace. Clean commercial product look, no cuts.
```
GQ1 → `{{MOTION_LEVEL}}`: পাতলা = "noticeably", মাঝারি = "gently", ভারী = "slowly, the fabric holding its weight".

### G2 · Rigid (product still, camera moves)

**G2-A Main**
```
The {{PRODUCT}} stays standing upright on {{SURFACE}}, label unchanged and fully readable, shape fixed. It rotates very slowly by a few degrees while {{ACCENT}} drifts past behind it. The camera orbits gently around it. {{LIGHT}} creates a soft highlight running down one side. {{MOOD}} pace. Clean commercial product cinematography, no cuts.
```
**G2-B Close-up**
```
Close-up on {{DETAIL}} of the {{PRODUCT}}. The product does not move; its label and shape stay exactly as they are. The camera drifts slowly downward across the surface while light travels over it. {{LIGHT}}. Slow pace. Macro lens look, high detail, no cuts.
```
**G2-C Wide**
```
The {{PRODUCT}} sits on {{SURFACE}} in {{SETTING}}, centred and unchanged, with empty space above it. Light gradually brightens across the scene; {{ACCENT}} moves faintly in the air. The camera slowly tilts up from the base to the top. {{MOOD}} pace. Warm clean lifestyle look, no cuts.
```
GQ2 = একটু ঝাপসা → drop "and fully readable" and crop tighter.

### G3 · Reflective (only the light moves)

**G3-A Main**
```
The {{PRODUCT}} stays completely still on {{SURFACE}}, every edge and link unchanged and in sharp focus. Nothing moves except a soft highlight travelling slowly across the {{MATERIAL}}. The camera orbits by only a few degrees. {{LIGHT}}, controlled reflections, uncluttered surroundings. {{MOOD}} pace. Macro product look, no cuts.
```
**G3-B Close-up**
```
Extreme close-up on {{DETAIL}}. The product is locked in place and does not deform or change shape. A narrow band of light moves slowly across the surface, revealing its finish. The camera holds almost still. Soft directional light, no harsh glare. Slow pace. Macro lens, shallow depth of field, no cuts.
```
**G3-C Wide**
```
The {{PRODUCT}} rests on {{SURFACE}} against {{SETTING}}, still and unchanged, placed to one side with empty space beside it. The camera pulls back slowly while the highlight settles across the surface. {{LIGHT}}. {{MOOD}} pace. Clean jewellery photography look, no cuts.
```

### G4 · Flowing (the substance pours)

**G4-A Main** (the sealed container, written in the Rigid style)
```
The {{PRODUCT}} stays centred on {{SURFACE}}, container shape and label unchanged. The camera orbits slowly around it while {{LIGHT}} produces a soft glossy highlight along the glass. {{ACCENT}} drifts faintly behind. {{MOOD}} pace. Rich colour, shallow depth of field, no cuts.
```
**G4-B Close-up** (the pour)
```
Extreme close-up of {{MATERIAL}} in slow motion: a thick stream flows and pools, light catching the surface as it moves. The {{PRODUCT}} stays still at the edge of frame, unchanged. The camera holds steady with a very slow push in. {{LIGHT}}, glossy reflections. Slow, luxurious pace. Macro lens look, no cuts.
```
**G4-C Wide**
```
The {{PRODUCT}} sits closed on {{SURFACE}} in {{SETTING}}, unchanged and still, with empty space to one side. Warm light spreads slowly across the scene. The camera slowly pulls back. {{MOOD}} pace. Warm homely commercial look, no cuts.
```

### G5 · Fresh (wet by default, dry variant below)

**G5-A Main**
```
The {{PRODUCT}} stays in place on {{SURFACE}}, shape and colour unchanged. Water droplets on the surface glisten and one slowly rolls down the side. A light mist drifts through the background. The camera pushes in slowly. {{LIGHT}} with crisp natural colour. Fresh and lively pace. Shallow depth of field, high detail, no cuts.
```
**G5-B Close-up**
```
Close-up on {{DETAIL}}. The produce does not move or deform. The camera tracks slowly from left to right while light shifts over the surface, revealing texture and colour variation. {{LIGHT}}. Steady appetising pace. Macro food photography look, rich natural colour, no cuts.
```
**G5-C Wide**
```
The {{PRODUCT}} fills {{SURFACE}}, arranged neatly and staying still, with empty space at the top of frame. The camera slowly pulls back and rises to reveal the full arrangement. {{LIGHT}} warming gradually. {{MOOD}} pace. Natural documentary food look, no cuts.
```
**G5 dry variant** (GQ5 = শুকনো; replaces G5-A, and the dry avoid terms apply to all three shots)
```
The {{PRODUCT}} stays in place on {{SURFACE}}, shape and colour unchanged and completely dry. No water and no mist. Light moves slowly across the surface, revealing grain and texture. The camera pushes in slowly. {{LIGHT}}, crisp natural colour. Steady pace. Shallow depth of field, high detail, no cuts.
```

## 2.4 Shot plans: when one ad uses two groups

| Situation | Main (A) | Close-up (B) | Wide (C) |
|---|---|---|---|
| Normal | own group | own group | own group |
| GQ4 = দুইটাই (default) | G4-A | G4-B | G4-C |
| GQ4 = ঢালা | G4-B pour, wider framing | G4-B | G4-C |
| GQ4 = বন্ধ কৌটা | G2-A | G2-B | G2-C |
| Rice or spice in a sealed bag | G2-A | G2-B | G2-C |
| Face in a product photo | Crop out the person | as normal | Person holds still, or crop |

The group is chosen per shot, not per ad.

## 2.5 Service templates

**S1 · Property** (one clip per room; no pans, because pans warp the walls)
```
The room in the image stays exactly as it is, with nothing moving and no people present. The camera pushes in slowly and steadily from the doorway toward the far wall. {{LIGHT}} through the windows, natural colour, furniture and layout unchanged. Calm, unhurried pace. Wide lens look, steady motion, no cuts.
```
**S2 · Finished result**
```
The {{SUBJECT}} in the image stays exactly as it is, clean and unchanged. The camera pushes in slowly and holds. {{LIGHT}}, natural colour, nothing in the scene moves or shifts. Calm, satisfied pace. Wide lens look, steady motion, no cuts.
```
**S3 · Person at work.** Generate in order of risk: A, then B, then C.

S3-A Tools (safest)
```
Close-up of the {{TOOLS}} laid out on the {{SURFACE}}. Nothing moves and nothing changes shape. Only a soft highlight travels slowly across them. The camera drifts slowly from left to right. Soft daylight, natural colour. Calm pace. Macro look, shallow depth of field, no cuts.
```
S3-B Hands (no faces in frame)
```
Close-up of the {{WORKER}}'s hands at work. The hands move slowly and steadily, one small controlled motion only. No faces in frame. Everything else in the scene stays unchanged. The camera holds almost still. Soft daylight, natural colour. Calm, careful pace. Shallow depth of field, no cuts.
```
S3-C Full scene (only if SQ8 = মুখসহ; three tries, then a still push-in made in editing)
```
The scene in the image stays exactly as it is. Everyone holds their pose, with only a very slight natural shift of the head and shoulders. Faces, hair, hands and clothing stay completely unchanged. Any mirror and its reflection stay exactly as they are. The camera pushes in slowly and steadily. Soft daylight, natural colour. Calm pace. Medium shot, no cuts.
```
**S4 · Poster or rate card.** No generation. A slow zoom and pan over his own image in editing, plus music, name and end card.

## 2.6 Avoid lists (negative prompt)

**Base, sent with every shot:**
```
text, letters, words, captions, subtitles, watermark, logo, changing label, morphing product shape, warped packaging, extra fingers, deformed hands, distorted face, jitter, flicker, sudden cut, scene change, camera shake, oversaturated colours, plastic texture, extra objects appearing
```

| Add for | Terms |
|---|---|
| G1 Soft | pattern drift, dissolving border, changing print |
| G3 Reflective | warped reflections, bent metal, smeared stones, mirror distortion |
| G4 Flowing | plastic-looking liquid, rubbery flow, splashing |
| G5 dry | water, droplets, mist, steam, wet surface |
| S1 Property | people, moving furniture, changing room layout, camera pan |
| S3 Person | changing faces, morphing beard, melting hair, extra people, warped reflection |
| Q6 answers | মানুষ → people · হাত → hands · পানি বা ধোঁয়া → water, mist, steam |

Not every video API has a separate negative-prompt field. During the model test (§3.4), check each model's API reference. Where there is no field, fold the five most important terms into the prompt as "no text, no watermark, no warping".

## 2.7 Bengali shot descriptions for C1

| Template | Line he reads |
|---|---|
| G1-A / B / C | কাপড় হালকা বাতাসে দুলছে · {DETAIL}-এর ক্লোজ-আপ · ঝুলছে, ক্যামেরা পিছিয়ে যাচ্ছে |
| G2-A / B / C | বোতল ধীরে ঘুরছে · লেবেলের ক্লোজ-আপ · টেবিলে রাখা, ক্যামেরা পিছিয়ে |
| G3-A / B / C | আলো গয়নার উপর দিয়ে যাচ্ছে · {DETAIL}-এর ক্লোজ-আপ · ক্যামেরা পিছিয়ে পুরোটা |
| G4-A / B / C | কৌটা স্থির, আলো পড়ছে · ঢালার ক্লোজ-আপ · কৌটা টেবিলে, ক্যামেরা পিছিয়ে |
| G5-A / B / C | পানির ফোঁটা চিকচিক করছে · গায়ের ক্লোজ-আপ · পুরো ঝুড়ি দেখা যাচ্ছে |
| G5 dry A | আলো ধীরে সরে যাচ্ছে, একদম শুকনো |
| S1 | প্রতিটা রুমে ক্যামেরা ধীরে ভেতরে যাচ্ছে |
| S3-A / B / C | সরঞ্জামের ক্লোজ-আপ · কাজ করা হাত · পুরো দোকান, ক্যামেরা ধীরে কাছে |

Post-production summary, shown under the three lines: `নাম, নাম্বার আর দাম ভিডিওর উপরে বসানো হবে — ভিডিওর ভেতরে না।`

## 2.8 The order line

Every order is logged as one line, from the first order onward:

```
ORD-000142 · B09 → G4 · GQ4=দুইটাই · shots G4-A, G4-B, G4-C · model seedance-1.0-pro-fast · 720p 9:16 · tries 2,3,2 · C1 ok · R1 👍
```

These lines are the data for later decisions: real retry rates per group, which model to keep, which questions people skip, and the test sets for P2 and P3.

---

# Part 3: The models

## 3.1 What needs a model, and when

| Job | Needed from | Model type |
|---|---|---|
| Turn the photo into three clips | P0 | Image-to-video |
| Bengali voiceover (optional, P6) | P1 | Text-to-speech |
| Music | P0 (library) | Music generation |
| Read typed answers and first messages | P2 | Small text model |
| Read voice notes | P2 | Speech-to-text (Bengali) |
| Read the photo: group, blur, watermark, face, count | P3 | Small vision model |
| Check clips for warping before delivery | P4 | Vision model plus frame comparison |
| WhatsApp buttons and lists | P1 | WhatsApp Cloud API (not a model, but a running cost) |

## 3.2 Image-to-video: the shortlist

All rows are image-to-video, with prices as published. **The 5-second clip column is my calculation** for one 720p 9:16 clip, without audio unless noted.

| Model | Route | Price | 5s clip, 720p | Clip lengths | Notes |
|---|---|---|---|---|---|
| **Seedance 1.0 Pro Fast** | BytePlus ModelArk | $1.00 / 1M tokens online; $0.50 offline | **$0.108** ($0.054 offline) | 2–12 s | Cheapest serious option. Older model, not on the current top-15 list |
| **Seedance 1.5 Pro** | BytePlus ModelArk | $1.20 / 1M tokens without audio; $0.60 offline | **$0.130** | 4–12 s | 480p, 720p, 1080p; first and last frame |
| Seedance 1.0 Pro | BytePlus ModelArk | $2.50 / 1M tokens; $1.25 offline | $0.270 | 2–12 s | The September report's pick, now beaten on price by the two above |
| Seedance 2.0 Mini | BytePlus ModelArk | $3.50 / 1M tokens | $0.378 | — | Priced for 480p and 720p only |
| Seedance 2.0 | BytePlus ModelArk | $7.00 / 1M tokens | $0.756 | 4–15 s | #3 on the image-to-video leaderboard |
| Seedance 2.5 | BytePlus ModelArk | $10.70 / 1M tokens | $1.156 | — | #1 on the leaderboard (Elo 1158) |
| **MiniMax H3** | MiniMax API | $0.08/s at 768p | **$0.40** | 4–15 s | #4 (Elo 1133). Native audio |
| **Wan 3.0** | Alibaba Model Studio | CNY 0.6/s at 720p (≈ $0.083) | **$0.42** | up to 30 s | #10 (Elo 1109). Same price in Frankfurt and US regions |
| **Kling 3.0** | Kling API | $0.084/s at 720p, silent | **$0.42** | 3–15 s | Outside the top 15 by Elo, but widely used. fal: $0.112/s |
| **Veo 3.1 Lite** | Gemini API | $0.05/s at 720p, audio included | $0.20 (4 s) / $0.30 (6 s) | 4, 6 or 8 s | No 5 s clip. No free tier |
| Veo 3.1 Fast | Gemini API | $0.10/s at 720p | $0.40 (4 s) | 4, 6 or 8 s | |
| Luma Ray 3.2 | Luma API | $0.06/s at 720p | $0.30 | — | From a September price check |

**How the Seedance figures are worked out.** BytePlus charges per token, where tokens = width × height × 24 fps × seconds ÷ 1024. A 720×1280 clip of 5 seconds is 108,000 tokens. At $1.00 per million that is $0.108. The same formula at Seedance 2.5's $10.70 gives $1.156, which matches CometAPI's published figure for a 720p 5-second clip, so the formula is right.

**Offline (batch) inference** halves the Seedance price. It suits orders that don't need delivery within minutes, which is most P0 orders. How long batch jobs actually take is not published in what I could read, so measure it in the test.

**Do not use:**
- **Sora 2**: removed from OpenAI's API on 24 September 2026.
- **Free tiers** of any platform: watermarks or no commercial licence.
- **Seedance 2.x "with video input" rates**: those are for video input. Ours is image input, so the higher "no video input" rates in the table apply.

## 3.3 What an ad costs to generate

Three 5-second clips at 720p, assuming **two tries per clip**. The real try rate is unknown until the pilot logs it. Taka at about ৳122 per US dollar; check the current rate.

| Model | Per ad (USD) | Per ad (৳, approx.) |
|---|---|---|
| Seedance 1.0 Pro Fast (online) | $0.65 | ৳79 |
| Seedance 1.0 Pro Fast (offline) | $0.32 | ৳40 |
| Seedance 1.5 Pro | $0.78 | ৳95 |
| Veo 3.1 Lite (6 s clips) | $1.80 | ৳220 |
| MiniMax H3 | $2.40 | ৳293 |
| Seedance 2.0 Mini | $2.27 | ৳277 |
| Kling 3.0 / Wan 3.0 | $2.52 | ৳307 |

Generation now costs about **৳40–300 per ad**, depending on the model. The deck's ৳195 figure assumed Seedance 1.0 Pro, which has since been undercut. Update that slide after the test.

## 3.4 Recommendation: test before choosing

The leaderboard ranks general clips judged by the public. It does not show how a model handles a saree border, a honey pour or a gold chain. Run one small test round in P0 before committing.

**Test round**
- **Photos:** 10 real seller photos, 2 per group, plus one service photo.
- **Models (7):** Seedance 1.0 Pro Fast, Seedance 1.5 Pro, Seedance 2.0 Mini, MiniMax H3, Wan 3.0, Kling 3.0, Veo 3.1 Lite.
- **Prompts:** the templates in Part 2, unchanged across models.
- **Cost:** 10 photos × 3 shots × 7 models, one try each, comes to about **$65 (৳7,900)**, by my calculation from the rates above.
- **Score each clip on:** product unchanged? label readable? motion as asked? any text or warping? would a seller post it?
- **Also record:** time to generate, whether a negative-prompt field exists, whether 9:16 works directly, and whether a cropped square still looks right (this sets the "দুইটাই" price).

**Expected outcome.** I can't confirm this until the test runs, but a likely result is:
- one cheap default for G1, G2 and G5 (probably a Seedance 1.x model);
- a stronger model for G3 Reflective and S3 faces (probably MiniMax H3 or Seedance 2.0), because those fail most and the extra cost is justified there.

Record the model per order in the order line (§2.8) so this can be checked against real retry rates later.

## 3.5 Text and vision model (P2 and P3)

| Model | Price per 1M tokens (in / out) | Use | Status |
|---|---|---|---|
| **Gemini 3.1 Flash-Lite** | $0.25 / $1.50 | Reading typed answers (P2), reading photos (P3) | Generally available |
| Gemini 3 Flash | $0.50 / $3.00 | If Flash-Lite misreads Banglish | Preview |
| Gemini 2.5 Flash-Lite | $0.10 / $0.40 | — | **Retired 16 Oct 2026; do not build on it** |

One photo read costs well under a tenth of a US cent. That's my estimate, assuming about 1,500 input and 300 output tokens per call; measure it in P3. Get the reply as a fixed JSON shape, never free prose:

```json
{"group": "G5", "variant": "dry", "product_guess_bn": "কাঁচা আম",
 "face": true, "people_count": 1, "products_count": 1,
 "blur": false, "watermark": false, "glare": false,
 "hook_options_bn": ["রঙ", "আকার", "তাজা ভাব"], "confidence": 0.82}
```

Test it against the P0–P2 photos already sorted by hand. If it agrees with the human-chosen group less than about nine times in ten, keep the confirmation tap.

## 3.6 Bengali voice (P1, optional)

| Service | Price | Bengali voices | Commercial use |
|---|---|---|---|
| **Azure Speech** | $15 / 1M characters (neural) | **bn-BD**: Nabanita (female), Pradeep (male), plus bn-IN voices | Yes |
| ElevenLabs | $0.08 / 1K characters (v3, Multilingual v2); $0.04 Flash | Bengali supported | Starter ($6/month) and above; not the free plan |

A 30-word Bengali script is about 200 characters. That's about $0.003 on Azure and $0.016 on ElevenLabs, negligible either way.

**Choose by ear, not by price.** Azure has voices labelled Bangladeshi Bengali (bn-BD). Most other Bengali voices sound Indian (Kolkata), which Bangladeshi buyers notice. Play both to three or four sellers before choosing.

## 3.7 Voice notes to text (P2)

| Service | Price | Bengali |
|---|---|---|
| ElevenLabs Scribe v2 | $0.22 / hour | Supported. ElevenLabs' own Bengali table shows 8.1% word error on FLEURS for Scribe v1 |
| Azure Speech (batch) | $0.18 / hour | Check bn-BD speech-to-text support before choosing |

A 20-second voice note costs a small fraction of a cent. Test on real Banglish voice notes from P0, because benchmark accuracy is measured on clean read speech, not market-stall audio.

## 3.8 Music

| Option | Price | Limit | Commercial use |
|---|---|---|---|
| Suno Pro | $10/month | **20 downloads/month** | Yes, for downloads made while subscribed |
| Suno Premier | $30/month | 60 downloads/month | Yes |
| Suno Free | $0 | — | **No** |

At 20 downloads a month, a new song for every ad won't work. **Build a library instead:** about 20 tracks, around 5 per mood (নরম, উৎসবের, আধুনিক, ঘরোয়া), downloaded once on Pro and reused. Rights to tracks you downloaded on Pro reportedly remain after cancelling. Suno doesn't guarantee copyright in AI music, so don't promise a client exclusive music.

## 3.9 WhatsApp Cloud API: correcting the deck

**The deck's statement that "replies inside 24 hours are free" is out of date.** Two pricing trackers (FlowCall, updated 4 Nov 2026; Drag, updated 21 Oct 2026) report that from **1 October 2026**:
- the first **1,000 service messages per number per month** are free;
- after that, service replies and utility messages inside the window cost the market's **utility rate**;
- **Bangladesh** now has its own rates: **$0.0037** per utility, authentication or service message and **$0.0732** per marketing message.

Meta's own marketing page still shows the older "free" wording (last modified May 2026). Check the current rate in WhatsApp Manager before launch.

**What this means for us:**
- One order sends us roughly 10 messages.
- Up to about 100 orders a month, the free 1,000 covers everything.
- At 1,000 orders a month (about 10,000 messages), the extra 9,000 cost about **$33 a month** (≈ ৳4,000). That's still small next to generation.
- Delivering a video **after** his 24-hour window needs a paid template ($0.0037 utility). Keep turnaround inside the window.
- **Never send promotional broadcasts as "marketing"** without budgeting for them: at $0.0732 each, they cost 20 times a utility message.
- Messages within 72 hours of a click on a Click-to-WhatsApp ad or Page button are free, according to Meta's page. If you advertise Golpo itself that way, those conversations cost nothing.

Update slide 9 ("The two channels") to match.

## 3.10 Editing and overlays

| Phase | Tool | Note |
|---|---|---|
| P0 | CapCut or similar, by hand | Fine at under 10 orders a day |
| P1+ | FFmpeg, scripted | Stitch clips, add music, logo and end card automatically |

**Bengali text in automated overlays is the trap to check first.** Bengali needs proper text shaping for its conjunct letters (যুক্তবর্ণ). Many simple video tools print it broken: "মিষ্টি" comes out with the letters split apart. Test with a few shop names that contain conjuncts. If it breaks, render each text overlay as a PNG with a shaping-aware renderer and composite the image instead. Use a Bengali font with a licence that allows commercial use.

## 3.11 All-in cost per ad (P0, product, estimated)

| Item | Cost |
|---|---|
| Generation, Seedance 1.0 Pro Fast, two tries per clip | $0.65 |
| Voice (if used), Azure | $0.003 |
| Music, from the reused library | ≈ $0 per ad |
| WhatsApp, inside the free 1,000 | $0 |
| **Total** | **≈ $0.65 (≈ ৳80)** |

This excludes your time, which in P0 is the largest cost by far (my estimate: about 8 minutes per order). With a stronger model for Reflective and face work, those orders cost about ৳300.

## 3.12 Before committing: checklist

- [ ] Run the test round (§3.4) and record scores per group and model.
- [ ] Confirm the Seedance 1.0 Pro Fast resolutions and 9:16 support in the BytePlus console. The model page lists the resolutions as "not specified".
- [ ] Measure how long Seedance offline jobs take.
- [ ] Check each video API for a negative-prompt field.
- [ ] Check the WhatsApp rates for Bangladesh in WhatsApp Manager.
- [ ] Play the Azure bn-BD and ElevenLabs voices to real sellers.
- [ ] Test Bengali overlays with conjunct-heavy names.
- [ ] Recheck every price in its console in the week you set customer prices.

## 3.13 Sources

Image-to-video rankings and prices
- [Artificial Analysis, image-to-video leaderboard](https://artificialanalysis.ai/video/leaderboard/image-to-video). Elo and per-minute prices, read 7 Nov 2026
- [Developers Digest, BytePlus video pricing](https://www.developersdigest.tech/models/video-generation/byteplus). All Seedance models, verified 18 Oct 2026
- [BytePlus, seedance-1.0-pro model page](https://docs.byteplus.com/en/docs/ModelArk/1587798). $2.50/M tokens, updated 31 Aug 2026
- [AI SDK, ByteDance provider](https://ai-sdk.dev/providers/ai-sdk-providers/bytedance). Seedance model IDs, durations, 9:16 support
- [CometAPI, Seedance 2.5 pricing](https://www.cometapi.com/seedance-2-5-api-pricing/). Cross-check for the token formula
- [Atlas Cloud, MiniMax H3 pricing](https://www.atlascloud.ai/blog/guides/minimax-h3-api-pricing). $0.08/s at 768p, Aug 2026
- [Alibaba Cloud, Wan 3.0](https://help.aliyun.com/en/model-studio/wan3-0-video). Per-second rates by region
- [ViDirect, Kling pricing by channel](https://vidirect.org/tools/kling/pricing). Official $0.084/s at 720p, verified 1 Oct 2026
- [Layer3 Labs, Veo 3.1 pricing](https://www.layer3labs.io/guides/veo-3-pricing). Lite / Fast / Standard, updated 25 Oct 2026
- [Teamday, video models by price](https://www.teamday.ai/blog/best-ai-video-models-2026). Luma, LTX and cross-checks, 23 Sep 2026
- [fal, image-to-video APIs](https://fal.ai/learn/tools/best-image-to-video-apis-2026). Reseller prices, Jun 2026

Text, vision and speech
- [Curlscape, Gemini API pricing](https://curlscape.com/blog/google-gemini-api-pricing-guide-2026). Flash-Lite prices and the 2.5 retirement, Jul 2026
- [Developers Digest, Azure Speech](https://www.developersdigest.tech/models/speech/azure). $15/M characters TTS, $0.18/h batch STT, 18 Oct 2026
- [json2video, Azure bn-BD voices](https://json2video.com/ai-voices/azure/voices/bn-bd-nabanitaneural/). Nabanita and Pradeep
- [Developers Digest, ElevenLabs](https://www.developersdigest.tech/models/speech/elevenlabs). TTS per 1K characters, Scribe $0.22/h, 18 Oct 2026
- [Dupple, ElevenLabs plans](https://dupple.com/pricing/elevenlabs). Commercial licence from Starter, 14 Oct 2026
- [ElevenLabs, Bengali speech-to-text](https://elevenlabs.io/speech-to-text/bengali). Bengali support and error rates

Music and messaging
- [DIY AI, Suno pricing](https://diyai.io/ai-tools/audio-generation/suno-pricing/). Plans, download caps and rights, 25 Oct 2026
- [FlowCall, WhatsApp API pricing](https://www.flowcall.co/blog/whatsapp-business-api-pricing). Bangladesh rates and the 1 Oct change, updated 4 Nov 2026
- [Drag, WhatsApp API pricing](https://www.dragapp.com/blog/whatsapp-business-api-pricing/). The 1 Oct change, updated 21 Oct 2026
- [WhatsApp Business, platform pricing](https://whatsappbusiness.com/products/platform-pricing/). Meta's page, older wording, modified May 2026
