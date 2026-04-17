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


def test_sort_bible_verse_blocks_with_ranges():
    text = """1 John 1:9
"“If we confess our sins, he is faithful and just and will forgive us our sins and purify us from all unrighteousness.”"

Acts 26:17-18
I now send you, to open their eyes…that they may receive forgiveness of sins…

Philippians 4:6-7
Be anxious for nothing… And the peace of God… shall guard your hearts

1 Corinthians 13: 4-7
 "Love is patient, 
love is kind. 
It does not envy, 
it does not boast, 
it is not proud.  
It does not dishonor others, 
it is not self-seeking, 
it is not easily angered, 
it keeps no record of wrongs.  
Love does not delight in evil but rejoices with the truth.  
It always protects, 
always trusts, 
always hopes, 
always perseveres.

Philippians 2:3-4
"Do nothing out of selfish ambition or vain conceit. Rather, in humility value others above yourselves, 4 not looking to your own interests but each of you to the interests of the others"

Ephesians 2:8–9 
"For it is by grace you have been saved, through faith… not by works, so that no one can boast."

Philippians 4:11–12 
I have learned to be content whatever the circumstances…
"""
    sorted_text = sort_bible_verse_blocks(text)

    assert sorted_text.index('Acts 26:17-18') < sorted_text.index('1 Corinthians 13: 4-7')
    assert sorted_text.index('Philippians 2:3-4') < sorted_text.index('Philippians 4:6-7')
    assert sorted_text.index('Ephesians 2:8–9') < sorted_text.index('Philippians 4:11–12')
