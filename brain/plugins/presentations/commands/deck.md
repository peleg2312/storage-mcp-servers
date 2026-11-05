---
description: Make a designed PowerPoint deck about a topic, a report folder or a document (Hebrew or English)
argument-hint: <topic, file or folder> [for <audience>] [in Hebrew]
---
Make a presentation: $ARGUMENTS

1. Gather the facts first: the files named, the current conversation, read-only tools where the topic needs live data.
   Write them down as a short list with their sources.
2. Language: the language of the request (Hebrew request = Hebrew deck), unless the user asked for another.
3. A monthly review, incident review, DR drill, proposal or status update: use that story (`deck_guide` with `story`).
4. A long deck or many facts: hand the facts, the audience, the goal and the language to the `deck-designer` agent.
   Otherwise follow the `make-deck` skill step by step yourself.
5. Answer with the file path and the PDF, the look number and the slide list. Use only facts from this session.
