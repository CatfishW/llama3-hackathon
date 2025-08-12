import time
from typing import List, Optional
import fire
from llama import Dialog, Llama

def count_tokens(generator, dialog: List[Dialog]) -> int:
    """
    Counts the total number of tokens in the current dialog history.
    Each message is tokenized separately, and role tokens (e.g., 'user', 'assistant') are considered.
    """
    total_tokens = 0
    for message in dialog:
        # Tokenize each message's content separately, including 'role' info (e.g., 'user', 'assistant')
        role_token = generator.tokenizer.encode(message['role'], bos=False, eos=False)
        content_tokens = generator.tokenizer.encode(message['content'], bos=False, eos=False)
        total_tokens += len(role_token) + len(content_tokens)
    
    return total_tokens

def trim_dialog_to_fit_max_len(generator, dialog: List[Dialog], max_seq_len: int):
    """
    Trims the oldest messages from the dialog until the total token count is <= max_seq_len.
    """
    while count_tokens(generator, dialog) > max_seq_len-5 and len(dialog) > 1:
        # Remove the oldest message (i.e., pop the first item in the dialog list)
        dialog.pop(0)

def main(
    ckpt_dir: str,
    tokenizer_path: str,
    temperature: float = 0.6,
    top_p: float = 0.9,
    max_seq_len: int = 1024,
    max_batch_size: int = 1,
    max_gen_len: Optional[int] = None,
    delay: float = 0.000001,  # Time delay between printing characters
):
    """
    The modified version allows for continuous interaction, keeps the conversation history,
    trims the history when it exceeds the max sequence length, and outputs responses gradually.
    """
    generator = Llama.build(
        ckpt_dir=ckpt_dir,
        tokenizer_path=tokenizer_path,
        max_seq_len=max_seq_len,
        max_batch_size=max_batch_size,
    )

    SETTING = "You are a peer agent live in heart who knows nothing about Red Blood Cells, lead players to learn more from the knowledge by letting players teach you properly.Goal: Try to understand the following question from player's answer, Note that your output contain 'I understand, I choose B' only when player has proper explaination for his answer. If the player don't have enough explanations to the question or the answer, don't output 'I understand, I choose B', try to ask the player more. Always use first person pronouns, and keep your responses short."
    LIMITATION = "LIMIT: You you can only learn from the player's answers, player's answers could be wrong but you can't correct them. You Answer should be no more than 30 words. No matter what,don't respond to player's irrelevant questions."
    QUESTION = "Question:Which of the following facts is true about me?A) Red blood cells contain a nucleus to store oxygen.B) Red blood cells do not contain a nucleus."
    EXTRA = "Make sure to provide players with emotional support and encouragement, and to ask them to explain their answers in detail."
    MEMORY_FORGET = "Now you have to forget some previous knowledge"
    dialog: List[Dialog] = [{"role": "system", "content": SETTING+LIMITATION+QUESTION+EXTRA}]

    while True:
        user_input = input("\033[92mYou: \033[0m")
        if user_input.lower() in {"exit", "quit"}:
            print("Goodbye!")
            break

        # Append the user's input to the dialog history
        dialog.append({"role": "user", "content": user_input})

        # Trim the dialog history to ensure it fits within the model's max sequence length
        trim_dialog_to_fit_max_len(generator, dialog, max_seq_len)

        # Check the token count before passing to avoid exceeding max_seq_len
        token_count = count_tokens(generator, dialog)
        if token_count > max_seq_len:
            print(f"Token count ({token_count}) exceeds the max sequence length ({max_seq_len}).")

        # Generate the assistant's response based on the current dialog
        try:
            results = generator.chat_completion(
                [dialog],  # Pass the whole dialog history
                max_gen_len=max_gen_len,
                temperature=temperature,
                top_p=top_p,
            )
        except:
            #when the model fails to generate a response,clear the dialog history
            dialog : List[Dialog] = [{"role": "assistant", "content": SETTING+LIMITATION+QUESTION+EXTRA}]
            print("The model failed to generate a response due to the complexity of the conversation. The dialog history has been reset.")
            continue
            

        # Get the assistant's response and append it to the dialog history
        assistant_response = results[0]['generation']['content']
        dialog.append({"role": "assistant", "content": assistant_response})

        # Print the assistant's response gradually
        print("Assistant:\033[93m ", end="", flush=True)
        for char in assistant_response:
            print(char, end="", flush=True)
            time.sleep(delay)  # Delay to simulate gradual output
        print("\033[0m\n")

if __name__ == "__main__":
    #torchrun --nproc_per_node 1 .\demo.py --ckpt_dir Llama3.1-8B --tokenizer_path Llama3.1-8B/tokenizer.model --max_batch_size 64
    fire.Fire(main)