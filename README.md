# 🎯 SEO Agency 2026

**Automated GEO/Technical SEO for WordPress** - A unified platform for 2026 AI-optimized content.

## 🚀 Quick Start

```bash
# 1. Clone the repo
git clone https://github.com/YOUR_USERNAME/seo-agency-2026.git
cd seo-agency-2026

# 2. Create virtual environment
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Configure credentials
cp .env.example .env
# Edit .env with your WordPress credentials

# 5. Run the CLI
python -m workflows.cli
```

## 📋 Features

### Technical SEO Fixes
- **Broken Links (404s)** - Auto-create 301 redirects
- **Orphan Pages** - Link to high-traffic parents
- **Redirect Chains** - Flatten A→B→C to A→C
- **IndexNow** - Instant search engine notification

### GEO (Generative Engine Optimization)
- **Answer Capsules** - 120-150 char AI-citable summaries
- **Inverted Pyramid** - Conclusions in top 10%
- **E-E-A-T Signals** - First-person experience markers
- **Schema Generation** - Product, FAQ, HowTo JSON-LD

### Validation
- **Live Verification** - Confirms fixes on real site
- **Retry Logic** - 3 attempts before failure
- **Audit Reports** - Detailed before/after scoring

## 📁 Structure

```
seo-agency-2026/
├── core/               # Shared WordPress utilities
├── modules/
│   ├── technical/      # 404s, orphans, redirects
│   ├── geo/           # Auditor, rewriter, schema
│   └── marketing/     # CTAs, affiliate (future)
├── validation/        # Live site verification
├── workflows/         # CLI and runners
├── reports/          # Generated reports
└── backups/          # Atomic backups
```

## 🔒 Security

- `.env` files are gitignored
- Credentials never committed
- Atomic backups before every change
- Human-in-the-loop approval for destructive actions

## 📊 Success Metrics

| Metric | Target |
|--------|--------|
| Technical Health | 100% (0 Ahrefs errors) |
| GEO Score | 80+ on all posts |
| AI Citations | Tracked in Perplexity/ChatGPT |

## 🛠️ Requirements

- Python 3.9+
- WordPress site with REST API enabled
- WordPress Application Password ([How to create](https://make.wordpress.org/core/2020/11/05/application-passwords-integration-guide/))

## 📜 License

MIT License - See LICENSE file
