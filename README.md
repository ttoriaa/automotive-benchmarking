# automotive-benchmarking

Quick entry for Dongchedi workflows and reusable skills.

## Skills Quick Entry

### 1) dongchedi-charging-confluence-pipeline

Use when:
- You need one workflow to run daily Dongchedi charging processing and publish or update Confluence.

Skill file:
- [.github/skills/dongchedi-charging-confluence-pipeline/SKILL.md](.github/skills/dongchedi-charging-confluence-pipeline/SKILL.md)

Quick invoke:
- /dongchedi-charging-confluence-pipeline
- /dongchedi-charging-confluence-pipeline date=2026-06-17 publish=false

### 2) dongchedi-charging-performance-summary

Use when:
- You need structured extraction and comparison of charging fields from Dongchedi parameter pages.

Skill file:
- [.github/skills/dongchedi-charging-performance-summary/SKILL.md](.github/skills/dongchedi-charging-performance-summary/SKILL.md)

Quick invoke:
- /dongchedi-charging-performance-summary 对这 5 个懂车帝 URL 生成充电性能对比总结

### 3) dongchedi-site-sync-after-daily

Use when:
- Daily CSV and Confluence update are done, and you want to sync website pages.
- You need to refresh data, dashboard, and insights pages together.

Skill file:
- [.github/skills/dongchedi-site-sync-after-daily/SKILL.md](.github/skills/dongchedi-site-sync-after-daily/SKILL.md)

Quick invoke:
- /dongchedi-site-sync-after-daily date=2026-06-17
- /dongchedi-site-sync-after-daily date=2026-06-17 deploy=false

## Full Skills Index

- [.github/skills/README.md](.github/skills/README.md)
