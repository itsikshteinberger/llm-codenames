from langchain_core.messages import HumanMessage
from langchain_openai import ChatOpenAI
import re
import os

# Add your key here:
os.environ['OPENAI_API_KEY'] = 'add your key here'

llm_clue_giver = ChatOpenAI(model_name="gpt-4", temperature=0.7)
llm_guesser = ChatOpenAI(model_name="gpt-3.5-turbo", temperature=0.7)


def get_clue(target_words, neutral_words, assassin_words, previous_clues):
    target_list = ", ".join(sorted(list(target_words)))
    neutral_list = ", ".join(sorted(list(neutral_words)))
    assassin_list = ", ".join(sorted(list(assassin_words)))

    prompt = f"""
    You are the Clue Giver in a game of Codenames. Your goal is to get your partner (the Guesser) to select ALL of your target words using the fewest clues possible.

    ---
    BOARD STATE
    * TARGET WORDS (Your team must pick these): {target_list}
    * NEUTRAL WORDS (Picking these ends your turn): {neutral_list}
    * ASSASSIN WORDS (Picking these loses the game immediately): {assassin_list}
    * PREVIOUS CLUES GIVEN: {previous_clues if previous_clues else "None"}

    ---
    RULES
    1. Your clue MUST be a single, English word.
    2. Your clue MUST NOT be any of the words currently on the board.
    3. Your clue should relate to at least two of the TARGET WORDS.
    4. Your clue MUST NOT relate strongly to the NEUTRAL or ASSASSIN words.
    5. You MUST output your response in the format: CLUE, NUMBER.
        NUMBER: The count of target words your clue relates to (maximum {len(target_words)}).

    Based on the board state, generate the best possible clue.
    """

    response = llm_clue_giver.invoke([HumanMessage(content=prompt)]).content

    match = re.search(r"(\w+),\s*(\d+)", response)
    if match:
        clue = match.group(1).upper()
        number = min(int(match.group(2)), len(target_words))
        return clue, number

    print(f"\n[Clue Giver Error] Response: '{response}'. Defaulting to 'SAFE, 1'.")
    return "SAFE", 1


def get_guesses(clue, number, unguessed_words):

    words_to_pick = sorted(list(unguessed_words))

    prompt = f"""
    You are the Guesser in a game of Codenames. The available words are: {", ".join(words_to_pick)}.

    ---
    CURRENT CLUE
    * Clue: {clue}
    * Count: {number} (Max words to guess is {number + 1} including bonus.)

    ---
    RULES
    1. Your turn ends immediately if you pick a Neutral or Assassin word.
    2. You should aim to pick up to {number} words, plus one optional bonus word.
    3. You MUST output your response as a comma-separated list of the words you want to pick (UPPERCASE).

    Based on the clue '{clue}' for '{number}' words, list the words you will pick in order.
    """

    response = llm_guesser.invoke([HumanMessage(content=prompt)]).content

    guesses = [w.strip().upper() for w in response.split(',') if w.strip().upper() in unguessed_words]

    return guesses[:number + 1]

