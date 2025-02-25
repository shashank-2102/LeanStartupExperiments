import random
import time
from dataclasses import asdict, dataclass
from typing import Callable, Literal
from transformers import pipeline, AutoTokenizer, AutoModelForCausalLM
import mesop as me
from markupsafe import escape
import torch


Role = Literal["user", "bot"]


_APP_TITLE = "Business Model Canvas Generator"
_BOT_AVATAR_LETTER = "M"
_EMPTY_CHAT_MESSAGE = "Get started with an example"
_EXAMPLE_USER_QUERIES = (
  "What is a Business Model Canvas?",
  "What are your capabilities?",
  "I have a startup idea, can you help me map it out?",
)
_CHAT_MAX_WIDTH = "800px"
_MOBILE_BREAKPOINT = 640


@dataclass(kw_only=True)
class ChatMessage:
  """Chat message metadata."""

  role: Role = "user"
  content: str = ""
  edited: bool = False
  # 1 is positive
  # -1 is negative
  # 0 is no rating
  rating: int = 0


@me.stateclass
class State:
  input: str
  output: list[ChatMessage]
  in_progress: bool
  sidebar_expanded: bool = False
  # Need to use dict instead of ChatMessage due to serialization bug.
  # See: https://github.com/google/mesop/issues/659
  history: list[list[dict]]



def respond_to_chat(input: str, history: list[ChatMessage]):
    """Process messages"""
    

    tokenizer = AutoTokenizer.from_pretrained("microsoft/Phi-3-mini-4k-instruct", trust_remote_code=True)

    model = AutoModelForCausalLM.from_pretrained(
        "microsoft/Phi-3-mini-4k-instruct", 
        device_map="cpu", 
        torch_dtype="auto", 
        trust_remote_code=True, 
    )

    # print(tokenizer.model_max_length)


    formatted_history = []
    if isinstance(history, list):
        for msg in history:
            if isinstance(msg, ChatMessage):
                role = "assistant" if msg.role == "bot" else "user"
                formatted_history.append({"role": role, "content": msg.content})
    
    print(formatted_history)


    # Create messages list with system prompt
    messages = [
        {
            "role": "system",
            "content": """You are a helpful AI assistant specialized in Business Model Canvas (BMC). 
            You help users analyze and create their Business Model Canvas by addressing the nine key components:
            1. Customer Segments
            2. Value Propositions
            3. Channels
            4. Customer Relationships
            5. Revenue Streams
            6. Key Resources
            7. Key Activities
            8. Key Partnerships
            9. Cost Structure"""
        }
    ]
    
    # Add history and current input
    messages += formatted_history
    messages.append({"role": "user", "content": input})

    # pipe = pipeline(
    # "text-generation",
    # model=model,
    # tokenizer=tokenizer,
    # )

    # generation_args = {
    #     "max_new_tokens": 500,
    #     "return_full_text": False,
    #     "temperature": 0.7,
    #     "do_sample": True,
    # }

  ##########

    # formatted_input = "\n".join([f"{msg['role']}: {msg['content']}" for msg in messages])

    # # output = pipe(formatted_input, **generation_args)
    # inputs = tokenizer(formatted_input, return_tensors="pt", padding=True)
    
    # outputs = model.generate(
    #     inputs["input_ids"],
    #     max_new_tokens=500,
    #     do_sample=True,
    #     temperature=0.7,
    #     pad_token_id=tokenizer.eos_token_id
    # )

    # # response = output[0]['generated_text']
    # response = tokenizer.decode(outputs[0], skip_special_tokens=True)
    
    # # Clean up response
    # response = response.replace(formatted_input, "").strip()
    # response = response.replace("assistant:", "").replace("Assistant:", "").strip()
   
    # print(response)
    # yield response

    pipe = pipeline( 
    "text-generation", 
    model=model, 
    tokenizer=tokenizer, 
    ) 

    generation_args = { 
        "max_new_tokens": 500, 
        "return_full_text": False, 
        "temperature": 0.7, 
        "do_sample": True, 
    } 

    output = pipe(messages, **generation_args) 
    print(output[0]['generated_text']) 
    yield output[0]['generated_text']

def on_load(e: me.LoadEvent):
  me.set_theme_mode("system")


@me.page(
#   security_policy=me.SecurityPolicy(
#     allowed_iframe_parents=["https://google.github.io", "https://huggingface.co"]
#   ),
  title="Business Model Canvas Chat",
  path="/",
  on_load=on_load,
)
def page():

  state = me.state(State)

  with me.box(
    style=me.Style(
      background=me.theme_var("surface-container-lowest"),
      display="flex",
      flex_direction="column",
      height="100%",
    )
  ):
    with me.box(
      style=me.Style(
        display="flex", flex_direction="row", flex_grow=1, overflow="hidden"
      )
    ):
      with me.box(
        style=me.Style(
          background=me.theme_var("surface-container-low"),
          display="flex",
          flex_direction="column",
          flex_shrink=0,
          position="absolute"
          if state.sidebar_expanded and _is_mobile()
          else None,
          height="100%" if state.sidebar_expanded and _is_mobile() else None,
          width=300 if state.sidebar_expanded else None,
          z_index=2000,
        )
      ):
        sidebar()

      with me.box(
        style=me.Style(
          display="flex",
          flex_direction="column",
          flex_grow=1,
          padding=me.Padding(left=60)
          if state.sidebar_expanded and _is_mobile()
          else None,
        )
      ):
        header()
        with me.box(style=me.Style(flex_grow=1, overflow_y="scroll")):
          if state.output:
            chat_pane()
          else:
            examples_pane()
        chat_input()


def sidebar():
  state = me.state(State)
  with me.box(
    style=me.Style(
      display="flex",
      flex_direction="column",
      flex_grow=1,
    )
  ):
    with me.box(style=me.Style(display="flex", gap=20)):
      menu_icon(icon="menu", tooltip="Menu", on_click=on_click_menu_icon)
      if state.sidebar_expanded:
        me.text(
          _APP_TITLE,
          style=me.Style(margin=me.Margin(bottom=0, top=14)),
          type="headline-6",
        )

    if state.sidebar_expanded:
      menu_item(icon="add", label="New chat", on_click=on_click_new_chat)
    else:
      menu_icon(icon="add", tooltip="New chat", on_click=on_click_new_chat)

    if state.sidebar_expanded:
      history_pane()


def history_pane():
  state = me.state(State)
  for index, chat in enumerate(state.history):
    with me.box(
      key=f"chat-{index}",
      on_click=on_click_history,
      style=me.Style(
        background=me.theme_var("surface-container"),
        border=me.Border.all(
          me.BorderSide(
            width=1, color=me.theme_var("outline-variant"), style="solid"
          )
        ),
        border_radius=5,
        cursor="pointer",
        margin=me.Margin.symmetric(horizontal=10, vertical=10),
        padding=me.Padding.all(10),
        text_overflow="ellipsis",
      ),
    ):
      me.text(_truncate_text(chat[0]["content"]))


def header():
  state = me.state(State)
  with me.box(
    style=me.Style(
      align_items="center",
      background=me.theme_var("surface-container-lowest"),
      display="flex",
      gap=5,
      justify_content="space-between",
      padding=me.Padding.symmetric(horizontal=20, vertical=10),
    )
  ):
    with me.box(style=me.Style(display="flex", gap=5)):
      if not state.sidebar_expanded:
        me.text(
          _APP_TITLE,
          style=me.Style(margin=me.Margin(bottom=0)),
          type="headline-6",
        )

    with me.box(style=me.Style(display="flex", gap=5)):
      icon_button(
        key="",
        icon="dark_mode" if me.theme_brightness() == "light" else "light_mode",
        tooltip="Dark mode"
        if me.theme_brightness() == "light"
        else "Light mode",
        on_click=on_click_theme_brightness,
      )


def examples_pane():
  with me.box(
    style=me.Style(
      margin=me.Margin.symmetric(horizontal="auto"),
      padding=me.Padding.all(15),
      width=f"min({_CHAT_MAX_WIDTH}, 100%)",
    )
  ):
    with me.box(style=me.Style(margin=me.Margin(top=25), font_size=24)):
      me.text(_EMPTY_CHAT_MESSAGE)

    with me.box(
      style=me.Style(
        display="flex",
        flex_direction="column" if _is_mobile() else "row",
        gap=20,
        margin=me.Margin(top=25),
      )
    ):
      for index, query in enumerate(_EXAMPLE_USER_QUERIES):
        with me.box(
          key=f"query-{index}",
          on_click=on_click_example_user_query,
          style=me.Style(
            background=me.theme_var("surface-container-highest"),
            border_radius=15,
            padding=me.Padding.all(20),
            cursor="pointer",
          ),
        ):
          me.text(query)


def chat_pane():
  state = me.state(State)
  with me.box(
    style=me.Style(
      background=me.theme_var("surface-container-lowest"),
      color=me.theme_var("on-surface"),
      display="flex",
      flex_direction="column",
      margin=me.Margin.symmetric(horizontal="auto"),
      padding=me.Padding.all(15),
      width=f"min({_CHAT_MAX_WIDTH}, 100%)",
    )
  ):
    for index, msg in enumerate(state.output):
      if msg.role == "user":
        user_message(message=msg)
      else:
        bot_message(message_index=index, message=msg)

    if state.in_progress:
      with me.box(key="scroll-to", style=me.Style(height=250)):
        pass


def user_message(*, message: ChatMessage):
  with me.box(
    style=me.Style(
      display="flex",
      gap=15,
      justify_content="end",
      margin=me.Margin.all(20),
    )
  ):
    with me.box(
      style=me.Style(
        background=me.theme_var("surface-container-low"),
        border_radius=10,
        color=me.theme_var("on-surface-variant"),
        padding=me.Padding.symmetric(vertical=0, horizontal=10),
        width="66%",
      )
    ):
      me.markdown(message.content)


def bot_message(*, message_index: int, message: ChatMessage):
  with me.box(style=me.Style(display="flex", gap=15, margin=me.Margin.all(20))):
    text_avatar(
      background=me.theme_var("primary"),
      color=me.theme_var("on-primary"),
      label=_BOT_AVATAR_LETTER,
    )

    # Bot message response
    with me.box(style=me.Style(display="flex", flex_direction="column")):
      me.markdown(
        message.content,
        style=me.Style(color=me.theme_var("on-surface")),
      )

      # Actions panel
      with me.box():
        icon_button(
          key=f"thumb_up-{message_index}",
          icon="thumb_up",
          is_selected=message.rating == 1,
          tooltip="Good response",
          on_click=on_click_thumb_up,
        )
        icon_button(
          key=f"thumb_down-{message_index}",
          icon="thumb_down",
          is_selected=message.rating == -1,
          tooltip="Bad response",
          on_click=on_click_thumb_down,
        )
        icon_button(
          key=f"restart-{message_index}",
          icon="restart_alt",
          tooltip="Regenerate answer",
          on_click=on_click_regenerate,
        )


def chat_input():
  state = me.state(State)
  with me.box(
    style=me.Style(
      background=me.theme_var("surface-container")
      if _is_mobile()
      else me.theme_var("surface-container"),
      border_radius=16,
      display="flex",
      margin=me.Margin.symmetric(horizontal="auto", vertical=15),
      padding=me.Padding.all(8),
      width=f"min({_CHAT_MAX_WIDTH}, 90%)",
    )
  ):
    with me.box(
      style=me.Style(
        flex_grow=1,
      )
    ):
      me.native_textarea(
        autosize=True,
        key="chat_input",
        min_rows=4,
        on_blur=on_chat_input,
        shortcuts={
          me.Shortcut(shift=True, key="Enter"): on_submit_chat_msg,
        },
        placeholder="Enter your prompt",
        style=me.Style(
          background=me.theme_var("surface-container")
          if _is_mobile()
          else me.theme_var("surface-container"),
          border=me.Border.all(
            me.BorderSide(style="none"),
          ),
          color=me.theme_var("on-surface-variant"),
          outline="none",
          overflow_y="auto",
          padding=me.Padding(top=16, left=16),
          width="100%",
        ),
        value=state.input,
      )
    with me.content_button(
      disabled=state.in_progress,
      on_click=on_click_submit_chat_msg,
      type="icon",
    ):
      me.icon("send")


@me.component
def text_avatar(*, label: str, background: str, color: str):
  me.text(
    label,
    style=me.Style(
      background=background,
      border_radius="50%",
      color=color,
      font_size=20,
      height=40,
      line_height="1",
      margin=me.Margin(top=16),
      padding=me.Padding(top=10),
      text_align="center",
      width="40px",
    ),
  )


@me.component
def icon_button(
  *,
  icon: str,
  tooltip: str,
  key: str = "",
  is_selected: bool = False,
  on_click: Callable | None = None,
):
  selected_style = me.Style(
    background=me.theme_var("surface-container-low"),
    color=me.theme_var("on-surface-variant"),
  )
  with me.tooltip(message=tooltip):
    with me.content_button(
      type="icon",
      key=key,
      on_click=on_click,
      style=selected_style if is_selected else None,
    ):
      me.icon(icon)


@me.component
def menu_icon(
  *, icon: str, tooltip: str, key: str = "", on_click: Callable | None = None
):
  with me.tooltip(message=tooltip):
    with me.content_button(
      key=key,
      on_click=on_click,
      style=me.Style(margin=me.Margin.all(10)),
      type="icon",
    ):
      me.icon(icon)


@me.component
def menu_item(
  *, icon: str, label: str, key: str = "", on_click: Callable | None = None
):
  with me.box(on_click=on_click):
    with me.box(
      style=me.Style(
        background=me.theme_var("surface-container-high"),
        border_radius=20,
        cursor="pointer",
        display="inline-flex",
        gap=10,
        line_height=1,
        margin=me.Margin.all(10),
        padding=me.Padding(top=10, left=10, right=20, bottom=10),
      ),
    ):
      me.icon(icon)
      me.text(label, style=me.Style(height=24, line_height="24px"))


# Event Handlers


def on_click_example_user_query(e: me.ClickEvent):
  """Populates the user input with the example query"""
  state = me.state(State)
  _, example_index = e.key.split("-")
  state.input = _EXAMPLE_USER_QUERIES[int(example_index)]
  me.focus_component(key="chat_input")


def on_click_thumb_up(e: me.ClickEvent):
  """Gives the message a positive rating"""
  state = me.state(State)
  _, msg_index = e.key.split("-")
  msg_index = int(msg_index)
  state.output[msg_index].rating = 1


def on_click_thumb_down(e: me.ClickEvent):
  """Gives the message a negative rating"""
  state = me.state(State)
  _, msg_index = e.key.split("-")
  msg_index = int(msg_index)
  state.output[msg_index].rating = -1


def on_click_new_chat(e: me.ClickEvent):
  """Resets messages."""
  state = me.state(State)
  if state.output:
    state.history.insert(0, [asdict(messages) for messages in state.output])
  state.output = []
  me.focus_component(key="chat_input")


def on_click_history(e: me.ClickEvent):
  """Loads existing chat from history and saves current chat"""
  state = me.state(State)
  _, chat_index = e.key.split("-")
  chat_messages = [
    ChatMessage(**chat) for chat in state.history.pop(int(chat_index))
  ]
  if state.output:
    state.history.insert(0, [asdict(messages) for messages in state.output])
  state.output = chat_messages
  me.focus_component(key="chat_input")


def on_click_theme_brightness(e: me.ClickEvent):
  """Toggles dark mode."""
  if me.theme_brightness() == "light":
    me.set_theme_mode("dark")
  else:
    me.set_theme_mode("light")


def on_click_menu_icon(e: me.ClickEvent):
  """Expands and collapses sidebar menu."""
  state = me.state(State)
  state.sidebar_expanded = not state.sidebar_expanded


def on_chat_input(e: me.InputBlurEvent):
  """Capture chat text input on blur."""
  state = me.state(State)
  state.input = e.value


def on_click_regenerate(e: me.ClickEvent):
  """Regenerates response from an existing message"""
  state = me.state(State)
  _, msg_index = e.key.split("-")
  msg_index = int(msg_index)

  # Get the user message which is the previous message
  user_message = state.output[msg_index - 1]
  # Get bot message to be regenerated
  assistant_message = state.output[msg_index]
  assistant_message.content = ""
  state.in_progress = True
  yield

  start_time = time.time()
  # Send in the old user input and chat history to get the bot response.
  # We make sure to only pass in the chat history up to this message.
  output_message = respond_to_chat(
    user_message.content, state.output[:msg_index]
  )
  for content in output_message:
    assistant_message.content += content
    # TODO: 0.25 is an abitrary choice. In the future, consider making this adjustable.
    if (time.time() - start_time) >= 0.25:
      start_time = time.time()
      yield

  state.in_progress = False
  me.focus_component(key="chat_input")
  yield


def on_submit_chat_msg(e: me.TextareaShortcutEvent):
  state = me.state(State)
  state.input = e.value
  yield
  yield from _submit_chat_msg()


def on_click_submit_chat_msg(e: me.ClickEvent):
  yield from _submit_chat_msg()


def _submit_chat_msg():
  """Handles submitting a chat message."""
  state = me.state(State)
  if state.in_progress or not state.input:
    return
  input = state.input
  # Clear the text input.
  state.input = ""
  yield

  output = state.output
  if output is None:
    output = []
  output.append(ChatMessage(role="user", content=input))
  state.in_progress = True
  me.scroll_into_view(key="scroll-to")
  yield

  start_time = time.time()
  # # Send user input and chat history to get the bot response.
  # output_message = respond_to_chat(input, state.output)
  # assistant_message = ChatMessage(role="bot")
  # output.append(assistant_message)
  # state.output = output
  # for content in output_message:
  #   assistant_message.content += content
  #   # TODO: 0.25 is an abitrary choice. In the future, consider making this adjustable.
  #   if (time.time() - start_time) >= 0.25:
  #     start_time = time.time()
  #     yield
  assistant_message = ChatMessage(role="bot")
  output.append(assistant_message)
  state.output = output
  
  # Get the response
  response = next(respond_to_chat(input, state.output[:-1]))  # Pass all messages except the last empty one
  assistant_message.content = response

  state.in_progress = False
  me.focus_component(key="chat_input")
  yield


# Helpers


def _is_mobile():
  return me.viewport_size().width < _MOBILE_BREAKPOINT


def _truncate_text(text, char_limit=100):
  """Truncates text that is too long."""
  if len(text) <= char_limit:
    return text
  truncated_text = text[:char_limit].rsplit(" ", 1)[0]
  return truncated_text.rstrip(".,!?;:") + "..."