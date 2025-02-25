
from transformers import pipeline, AutoTokenizer, AutoModelForCausalLM
import torch

def huggingface_LLM(input: str, history):
    """Process messages using Phi-3.5-mini-instruct model"""

    model = AutoModelForCausalLM.from_pretrained(
        "microsoft/Phi-3.5-mini-instruct",
        device_map="cpu",
        torch_dtype="auto",
        trust_remote_code=True,
    )
    
    tokenizer = AutoTokenizer.from_pretrained("microsoft/Phi-3.5-mini-instruct")

    # Format history
    formatted_history = []
    for msg in history:
        role = "assistant" if msg.role == "bot" else "user"
        formatted_history.append({"role": role, "content": msg.content})

    # Create messages list with system prompt
    messages = [
        {
            "role": "system",
            "content": """You are a helpful AI assistant specialized in Business Model Canvas (BMC)."""
        }
    ]
    
    # Add history and current input
    messages.extend(formatted_history)
    messages.append({"role": "user", "content": input})

    # Format into a single string
    formatted_input = "\n".join([f"{msg['role']}: {msg['content']}" for msg in messages])

    print("Encoding input...")
    inputs = tokenizer(formatted_input, return_tensors="pt", padding=True)
    
    print("Generating response...")
    outputs = model.generate(
        inputs["input_ids"],
        max_new_tokens=500,
        do_sample=True,
        temperature=0.7,
        pad_token_id=tokenizer.eos_token_id
    )
    
    response = tokenizer.decode(outputs[0], skip_special_tokens=True)
    
    # Clean up response
    response = response.replace(formatted_input, "").strip()
    response = response.replace("assistant:", "").replace("Assistant:", "").strip()
    
    yield response