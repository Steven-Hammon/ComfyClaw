

=== INSTRUCTIONS ===

#Based on the above CONTEXT evaluate what is most the CRUCIAL information in the #TOOL_CALL and the #TOOL_RESPONSE. The CONTEXT is only there to help you work out what the CRUCIAL information is. The Primary focus is on the #TOOL_CALL and the #TOOL_RESPONSE inside the OLDEST_LAST_RESPONSE.

## If the #TOOL_CALL is over 200 words, you must create a single paragraph, maximum 200 word summary of the #TOOL_CALL only. Use the CONTEXT above to determine what is the CRUCIAL information in the #TOOL_CALL that MUST be included. Anything that's not crucial, sumarise it with a broad overall gist of what it is. Then Prepend it with "Summarised version: ".

If the #TOOL_CALL is under 200 words, then just response with the same #TOOL_CALL word for word.

Ensure that your response is a JSON object with the exact same "#TOOL_CALL:" Key as the example JSON, followed by the maximum 200 word #TOOL_CALL.

## If the #TOOL_RESPONSE is over 200 words, you must create a single paragraph, maximum 200 word summary of the #TOOL_RESPONSE only. Use the CONTEXT above to determine what is the CRUCIAL information in the #TOOL_RESPONSE that MUST be included. Anything that's not crucial, summarise it with a broad overall gist of what it is. Then Prepend it with "Summarised version: ".

If the #TOOL_RESPONSE is under 200 words, then just response with the same #TOOL_RESPONSE word for word.

Ensure that your response is a JSON object with the exact same "#TOOL_RESPONSE:" Key as the example JSON, followed by the maximum 200 word #TOOL_RESPONSE.

## EXAMPLES:
{
  "#TOOL_CALL:" "BROWSER-GOTO: --url https://example.com",
  "#TOOL_RESPONSE:": "Summarised version: The website https://ai.vixra.org/author/steven_hammon is an AI paper website. The Crucial details are Steven Hammon's research papers, entitled, 'The Invisible War: Defending the Human Brain Against High-Engagement Psychological Warfare', 'Thermal Gravity: Vacuum Turbulence and the Refractive Geometry of Spacetime', 'Quantum Fluctuations as the Substrate of Spacetime', 'Velocity Time Dilation and Spacetime Frame Dragging', 'A Unified Model for Gravitational and Velocity Time Dilation' and 'Dark Energy as a Cosmic Shell Universe'. There is also a list of INTERACTIVE ELEMENTS."
}

{
  "#TOOL_CALL:" "Summarised version: FILE_WRITE-OVERWRITE: --path C:\\Workspace\\Stories\\Pip-Short_Story.txt --content In the dark warrens beneath a medieval city, a small grey mouse named Pip watched his world die. The Black Death crept through alleys like smoke, and Pip — wiser than his size — had worked out why. The lice and fleas that clung to every rat, every whisker and tail, were carrying the sickness from body to body. He was certain of it.\nHe went before the rats. He begged them to groom, to scrub, to drive the parasites away. The rats laughed. What could a mouse know of plague? They were rats. They had survived everything.\nNight after night, Pip returned. Night after night, they dismissed him. The bodies piled up — rat and human alike — and still no one listened. Then, exhausted and flea-bitten himself, Pip began to sicken.\nBut before the fever claimed him, he crossed paths with a haggard physician slumped in a doorway, surrounded by the dead. Pip scratched at the man's boot. When the physician looked down, Pip — in the only way a mouse can — caught a flea between his teeth and spat it toward a corpse. Then again. And again. The flea. The body. The flea.\nThe physician stared for a long moment. Something shifted behind his eyes.\nPip died before sunrise. The rats said nothing. But the physician rose, walked to his desk, and began to write.",
  "#TOOL_RESPONSE:": "Wrote 6270 characters to C:\\Workspace\\Stories\\The_Rock-Short_Story.txt"
}

