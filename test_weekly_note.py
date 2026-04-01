from a_weekly_note import sort_bible_verse_blocks


def test_sort_bible_verse_blocks():
    text = """1 Thessalonians 5:18
“Give thanks in all circumstances…”

Luke 22:42
“Not my will, but yours be done.”

Psalm 56:3
“When I am afraid, I put my trust in you.”
"""
    sorted_text = sort_bible_verse_blocks(text)

    # OT (Psalm) should come before NT (Luke, 1 Thessalonians)
    assert sorted_text.strip().startswith('Psalm 56:3')
    assert sorted_text.index('Luke 22:42') < sorted_text.index('1 Thessalonians 5:18')
