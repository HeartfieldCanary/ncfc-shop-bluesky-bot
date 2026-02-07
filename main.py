name: Post NCFC Promotions to Bluesky

on:
  schedule:
    # 17:00 GMT every Friday
    - cron: '0 17 * * 5'
  workflow_dispatch:

jobs:
  build-and-post:
    runs-on: ubuntu-latest

    steps:
      - name: Checkout repository
        uses: actions/checkout@v4

      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: '3.10'

      - name: Install dependencies
        run: |
          python -m pip install --upgrade pip
          pip install requests beautifulsoup4 atproto pillow

      - name: Run posting script
        env:
          BLUESKY_HANDLE: ${{ secrets.BLUESKY_HANDLE }}
          BLUESKY_APP_PASSWORD: ${{ secrets.BLUESKY_APP_PASSWORD }}
        run: python main.py
