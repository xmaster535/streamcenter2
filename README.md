# StreamCenter Auto-Updater

এটি একটি স্বয়ংক্রিয় স্ক্রিপ্ট যা **streamcenter.live** থেকে স্ট্রিম ইভেন্টগুলো সংগ্রহ করে এবং GitHub Actions ব্যবহার করে প্রতি 5 মিনিটে আপডেট করে।

## বৈশিষ্ট্য

- প্রতি 5 মিনিটে স্বয়ংক্রিয় আপডেট
- নতুন ইভেন্ট যুক্ত হলে সাথে সাথে আপডেট
- প্রতিটি ইভেন্টে original site এর team logo
- M3U এবং JSON ফরম্যাটে export

## GitHub তে সেটআপ করার নিয়ম

### ধাপ 1: GitHub Repository তৈরি করুন

1. GitHub এ নতুন repository তৈরি করুন
2. Repository কে **Private** না রেখে **Public** রাখুন (যাতে Actions কাজ করে)

### ধাপ 2: ফাইলগুলো আপলোড করুন

এই 3টি ফাইল আপনার repository তে আপলোড করুন:

```
streamcenter-scraper/
├── streamcenter.py      (মূল স্ক্রিপ্ট)
├── utils.py             (হেল্পার মডিউল)
├── requirements.txt     (প্যাকেজ লিস্ট)
└── .github/
    └── workflows/
        └── update.yml   (GitHub Actions)
```

### ধাপ 3: GitHub Actions enable করুন

1. Repository তে যান
2. **Settings** > **Actions** > **General** এ ক্লিক করুন
3. **Workflow permissions** এ গিয়ে **Read and write permissions** সিলেক্ট করুন
4. **Save** করুন

### ধাপ 4: Token সেট করুন (যদি প্রয়োজন হয়)

যদি আপনার repository private হয়, তাহলে:

1. GitHub এ **Settings** > **Secrets and variables** > **Actions** এ যান
2. **New repository secret** ক্লিক করুন
3. Name: `GH_TOKEN`
4. Value: আপনার GitHub Personal Access Token (classic)
   - Token পেতে: GitHub Settings > Developer settings > Personal access tokens > Generate new token
   - **repo** এবং **workflow** permissions দিন

### ধাপ 5: Workflow চালু করুন

1. Repository তে **Actions** ট্যাবে ক্লিক করুন
2. **Auto Update Streams** workflow দেখা যাবে
3. **Run workflow** ক্লিক করে ম্যানুয়ালি চালাতে পারেন

## ফাইল স্ট্রাকচার

```
├── streams.json    - সমস্ত ইভেন্টের JSON ডাটা (auto-generated)
├── streams.m3u     - M3U প্লেলিস্ট (auto-generated)
└── cache/          - ক্যাশ ফাইল (গিটহাবে আপলোড হয় না)
```

## API Response Format

প্রতিটি ইভেন্টে থাকছে:

```json
{
  "category": "Live Events",
  "eventName": "Team A vs Team B",
  "teamAFlag": "https://a.espncdn.com/i/teamlogos/soccer/500/382.png",
  "teamBFlag": "https://a.espncdn.com/i/teamlogos/soccer/500/384.png",
  "streaming_links": [...],
  "time": "19:00:00",
  "date": "13/05/2026"
}
```

## সাপোর্ট

কোনো সমস্যা হলে GitHub Issues তে জানান।