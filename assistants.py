from openai import OpenAI
client = OpenAI()

message = client.beta.threads.messages.create(
  thread_id="thread_idI9IJJbz3iG04vr5XfxX6SG",
  role="user",
  content="What is the best food in the world? Refer to your knowledge base files"
)

run = client.beta.threads.runs.create_and_poll(
  thread_id="thread_idI9IJJbz3iG04vr5XfxX6SG",
  assistant_id="asst_FTxFZVvCQdmPVfWQGJLSmzKX",
  instructions=""
)

if run.status == 'completed': 
  messages = client.beta.threads.messages.list(
    thread_id="thread_idI9IJJbz3iG04vr5XfxX6SG"
  )
  print(messages)
else:
  pass
  #print(run.status)