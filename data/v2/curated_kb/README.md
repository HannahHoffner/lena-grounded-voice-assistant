# LENA v2 Reviewed KB

This directory is the reviewed runtime source for clean LENA v2.

Runtime v2 does not scrape live pages. It reads `offers.json`, which is derived from the Stadt Leipzig Schadensminimierung page:

https://www.leipzig.de/leben-in-leipzig/gesundheit/suchthilfe/schadensminimierung

Rules:

- Include only offers listed on that page, plus directly linked detail facts when needed.
- Keep emergency behavior deterministic in code, not as a normal offer.
- Do not include broad v1 offers or Tafel unless the Leipzig page itself lists them.
- Every public fact needs source evidence and a review status.
- Source checks create report material only; a human reviews before publishing.

