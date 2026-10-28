# Collaborator task: reject invalid ticket ratings

Branch: `collab/rating-validation`.

A real bug currently exists on `main`: `save_rating(..., 99)` accepts an invalid score and adds 99 points to the operator's total. The UI exposes ratings 1–5, so tampered callback data must not corrupt persisted ratings.

## Work already contributed by z3wax

`tests/test_rating_validation.py` contains real SQLite acceptance tests for invalid scores, valid 1–5 scores, duplicates and unchanged persisted totals. The invalid-score subcases intentionally fail until the implementation is added. The6 earlier ticket/migration tests pass. This branch is a collaboration fixture, not a completed fix.

## Work for ABDULHODIY1

In `bot/database.py`, update `save_rating`:

- Accept only exact Python integers from 1 to 5; reject bool, floats, strings and None too.
- Invalid input returns False before writing to `ratings` or updating the operator's score/count.
- Preserve valid scores and the existing duplicate-rating behavior.
- Run the entire SQLite test suite and include the actual result in the PR.

## GitHub steps

Log into GitHub as `ABDULHODIY1`, fork this repository, then work from this collaboration branch. With Git:

```bash
git clone https://github.com/ABDULHODIY1/aiogram3x-support-bot.git pair-rating
cd pair-rating
git remote add upstream https://github.com/z3wax/aiogram3x-support-bot.git
git fetch upstream
git switch -c fix/rating-validation upstream/collab/rating-validation
python -m pip install aiosqlite
# Implement the validation described above.
python -m unittest discover -s tests -v
git add bot/database.py
git commit -m "Reject invalid ticket rating scores"
git push -u origin fix/rating-validation
```

Use the contributor account's own verified Git identity for its commit. On GitHub choose **Compare & pull request** with base `z3wax/aiogram3x-support-bot:main` and head `ABDULHODIY1/aiogram3x-support-bot:fix/rating-validation`.

Suggested title: `Reject invalid ticket rating scores`.

The PR includes z3wax's acceptance-test commit and ABDULHODIY1's implementation commit. After review and successful tests, the combined work can be squash-merged into one commit retaining both actual contributors. A co-author credit is appropriate after both contributions exist; opening a PR from another account alone does not create co-authorship. GitHub controls achievement eligibility.
