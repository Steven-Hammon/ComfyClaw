

=== INSTRUCTIONS ===

# Based on the CONTEXT above, evaluate how important this memory is. 

Also look at the big picture and deliver any deeper meaning that could be there, any insights that can be derived from the situation, and any relationship information that could tie in this memory to other crucial concepts, insights, information or situations. Try to keep the insights, deeper meaning, and possible relationships as significantly plausible. Use less certain language, like "It seems... ", "This could be...", "Maybe...", and other variations of uncertain language. Do not use "I", "my", or refer to any entity. No more than 100 words.

Also include some keywords for association.

## MEMORY_IMPORTANCE = a string whole number between 0 and 99, where 0 is totally forgettable and 99 is the most important memory anyone could possibly have. Make it a number as a string eg. ("22") because LLMs don't deal with integers. 

## INSIGHTS_MEANING_RELATIONSHIPS = Any insights, deeper meaning, or important relationship association information that could be valuable for long term memory.

## KEYWORDS = a series of 1-2 word keyword (2 word phrases), that describe the main category, either "Insights", "Processes", "Places", "People", "Concepts", or "Events", then a couple of keywords (2 word phrases) about content topics (Eg, a "Driving a Toyota" is maybe "Car", "Transport", "Driving", etc), and then another couple of keywords that link it to other types of similar concepts, processes or things (Eg, "Machinery Operation", "Navigation", "Going Home", etc),. Separate keywords with a comma in the string value.


## EXAMPLE JSON:

{
  "MEMORY_IMPORTANCE": "22",
  "INSIGHTS_MEANING_RELATIONSHIPS": "This could be a great way to work with other problems revolving around blah and blah. It seems like this could be touching on some aspects of the blah of the project, helping to establish a stronger blah. This idea might have fascinating implications in relation to blah.",
  "KEYWORDS": "Concepts, Ethics, Journalism, Mental Health, Democracy, MPAA"
}

Respond in JSON format, with the MEMORY_IMPORTANCE, INSIGHTS_MEANING_RELATIONSHIPS and KEYWORDS.