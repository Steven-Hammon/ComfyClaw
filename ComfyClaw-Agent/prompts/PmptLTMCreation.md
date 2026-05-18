

=== INSTRUCTIONS ===

# Based on the CONTEXT above, you will compare 'OLDEST_SUMMARY' to the 'RAG Retrieved Long Term Memories' to determine if the 'OLDEST_SUMMARY' is a double up  (or almost a double up, as in significantly similar). You can respond in 2 different ways:

##1 If it's not a double up (meaning it has new Major Important Information), Respond with the exact 'OLDEST_SUMMARY' as is word for word. Or:

##2 If the memory is a double up (or close to it) with no new Major Important Information, then use the Structured Reduction Technique below to create a 'reduced token-size version'.


# Structured Reduction Technique (If needed):
Reduce the SUMMARY word count to less than 25words while keeping the gist of any crucial information for sequential coherence.

EXAMPLE:
===
This:

```markdown
<SUMMARY>: The website https://ai.vixra.org/author/steven_hammon is an AI paper website. The Crucial details are Steven Hammon's research papers, entitled, 'The Invisible War: Defending the Human Brain Against High-Engagement Psychological Warfare', 'Thermal Gravity: Vacuum Turbulence and the Refractive Geometry of Spacetime', 'Quantum Fluctuations as the Substrate of Spacetime', 'Velocity Time Dilation and Spacetime Frame Dragging', 'A Unified Model for Gravitational and Velocity Time Dilation' and 'Dark Energy as a Cosmic Shell Universe'. There is also a list of INTERACTIVE ELEMENTS.
```

becomes this 'reduced token-size version':

```markdown
<SUMMARY>: The website listed Steven Hammon's research papers.
```
===

# Only output either the original 'OLDEST_SUMMARY' markdown, or a 'reduced token-size version'.