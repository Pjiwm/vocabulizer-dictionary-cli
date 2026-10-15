# Bundled data

## jiten_freq_global.csv.gz

Jiten global word frequency list (all media combined), gzipped.

- Source: https://jiten.moe/frequency-dictionaries
  (download: `https://api.jiten.moe/api/frequency-list/download?downloadType=csv`)
- Downloaded: 2026-10-15
- Columns: `Word` (term), `Form` (reading, hiragana), `Rank` (1 = most frequent)
- License: Creative Commons Attribution-ShareAlike 4.0 International (CC BY-SA 4.0),
  https://creativecommons.org/licenses/by-sa/4.0/

The file is committed so dictionary builds are reproducible. To update it, replace the
file with a fresh download and change the date above:

```sh
curl -sL "https://api.jiten.moe/api/frequency-list/download?downloadType=csv" | gzip -9 > data/jiten_freq_global.csv.gz
```
