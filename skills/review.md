---
name: review
reads: [diff]
writes: [review_notes]
---
# review
Read `diff`. Find the bugs that pass CI but break in production. Auto-fix the
obvious ones; flag the rest. Writes `review_notes`.
