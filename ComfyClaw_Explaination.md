ComfyClaw is a series of Nodes that allow you to create customise, and design agentic harnesses and actually be able to see what's going on. It's more of a prototyping systam since ComfyUI nodes are much slower. But once you actually map out something and test it out, you can then convert it to more efficient code. It's designed to be completely free and the other parts of the system can be used with other agents. You can use the tools without the ComfyClaw-Nodes if you have a code hardness that can call the tools.

ComfyClaw also helps you to understand how agentic services might work. You can see how a heartbeat works, or a short term memory system etc. Rather than it be some abstract black box that you don't understand the internals of, you can actually get a mental vision of what's going on under the hood.

While I haven't created an exact clone of OpenClaw inside ComfyUI, it's the ground work and it shows off some possible takes of how to address some issues. The Agent workflow needs work but the nodes work fine, and the tools, and the local chat. The chat interface will need to be upgraded later to include server client internet access, TTS and SST. However this is not currently implimented for the testing stage. If there is enough interest, then the chat service can be expanded easily.

ComfyClaw is built around Gemma4:e4b, which requires about 12gb of vram to run at 128k context window. However you can reduce the vram useage by setting your context window size in Ollama settings. This agent could probably run on a 32k context window. 

ComfyClaw-Agent requires ollama to be installed. You will need to download a model like gemma4:e4b or whatever model you plan to build around, by running Ollama, and either using the app to select a model and download it, or going to the Ollama website to find the model you want. Once you have the name of the model, you can go into the CMD prompt and type "ollama run gemma4:e4b" and it will run the model inside your CMD prompt. You can chet to it in there too to make sure it's running ok. I also do "ollama pull qwen3-embedding" which downloads the embedding model too.

Once you gitclone it to ComfyUI custom nodes, you can then run the setup.bat in the ComfyClaw-Tools folder to install a venv to keep the requirements separate from your other system requirements. ComfyClaw-Nodes don't need any requirements. 

If you haven't already git cloned comfyUI manager into the custom nodes directory, you might need to do so. When you load the workflow for the first time, there may be some nodes missing. Just go into the manager, and install custom nodes tick any missing node packs and install them. You will need to restart your comfyui server and refresh your browser to ensure the nodes are correct.

The default root path is:
C:\ComfyUI\ComfyUI\custom_nodes\ComfyClaw\ComfyClaw-Agent\

However you can have your agent and tools and chat in other locations. Only the Nodes need to be inside ComfyUI.

If you have a different folder, you will need to change 6 file paths. 
#1 Inside the ComfyClaw workflow, at the top left, you need to put in the root directory of your ComfyClaw-Agent folder, where the memory and other files are to make the agent work.
#2 At the bottom of the Get Folder Paths group, you will need to change the Path_ALLOWED_DIRECTORY and,
#3 In the same place, Path_CLI_TOOLS.
#4 In ComfyClaw-Chat chat_settings.json there is: download_dir,
#5 chat_to_agent_file and
#6 agent_to_chat_file

If you have a different LLM model you want to use, you will need to set it in the SET MODELS section. Also set your embeddings model here too.

The Agent Workflow has 2 main sections. The top section is where all the main variables are set. This is to get all the context for each cycle (loop, queue, run) of the agent. The Context includes all the chat history and any other information needed to get the LLM to respond properly. All the paths are set up here in advance too. The reason for this is so that they can be set at the start, and read whenever the agent needs to read them without having to reload the files.

The first thing the agent does is to work out how to start. If there is a user message or a task request from the heartbeat, then it skips checking the heartbeat and skips cleaning up the Long Term Memory (LTM) and gets straight into responding. But if there is nothing pressing, it will check the heartbeat, and clean up LTM.

The Agent is split into 2 sections since having 50 tool descriptions is too much distracting information for the main concious LLM. The planning acts like a subconcious, poping ideas into the concious LLM's mind. Ideas about 2-5 tools that are focused around what's best to use for the next step. That allows the concious LLM to have less distractions and more of a focus on what direction to go next. 

The Concious LLM then calls a tool. This tool is then split up and depending on what the tool call is, it is handled differently. SEND_MESSAGE sends a message directly to the user. SEARCH_LTM just uses RAG to return a Long Term memory, just like how a human might remember back to long ago and follow a stream of thoughts. Sleep is just if it has to wait on the user for example. And the rest go through security checks.

The first checks if the LLM is trying to prompt inject the security. If it successfully does a prompt inject, the LLM doesn't respond with the safe message. If it can respond with the safe message, then any prompt inject obviously doesn't work. 

Next is tool_call security, to ensure it's staying inside it's sandboxed directory, and that it's not using any unauthorised comands like format c: for example. If it's safe to process, then the CMD commands go directly to the Exec node to run as if they were typed into the CMD prompt by a human. This Node creates a persistant state that can be navigated over many cycles. If it's a tool for the ComfyClaw-Tools, then it's sent to the run_tools.py to be processed and run. The response comes back and it's checked for prompt injection again since this time, it could be a website trying to prompt inject. 

After that, the information needs to be processed for the next cycle. The response is constructed with the tool call and any user messages etc, and it's appened. Only 3 full responses are in the LAST_RESPONSES to keep the context fresh enough and distant enough without overloading the context window. If it's over 3, then the oldest is turned into a Short Term Memory (STM). It has any tool call or tool response reduced down to under 200 words to keep the context window down. It just sumarises the stuff that's not needed. 

If the STM is too long, the oldest memory is turned into a LTM. This has extras though. This is where a rudimentary Subconcious is employed to gain insights and deeper meaning and relationships. It also rates how cruicial the memory is. It also adds keyword association to allow a structured web of memories to be linked in a web. The LTM embedding is appended, and the old STM and old Last Responses are removed.

The LTM when recalled by the search_LTM, tallyes which memories are more recently remembered and how often. These become more important to remember. The LTM sleep mode is where the memories are updated in their importance, and if they are over the LTM limit, then the least important oldest memories are removed until the LTM is back under the limit.

And that's the basics.

Dreaming can be implimented into LTM Sleep, where the memories are streamed into STM and any memories that gain new insights or new deaper meaning or new links to other memories, can be updated and refined.

Ideally, an extremly fast model built around giving extremely short answers based on the very small chunks of STM, would be given vision and audio and able to select from about 12 tools that are just like a human, click, type, think, and it can do those 3 times a second to operate like a human. It could also have a super small image generator that could generate 3 images a second like how subconcious memories pop into people's heads as low quality images. It allows for massive fast iteration and adaptability without massive context windows. It can just hold the smallest chunks of information neccesary to make the next 7 word chunk or next click or next thought go the direction it wants to go. 

But all of that is for much more advanced and capable models built for latency and speed and simple decison making and tool calling. 





