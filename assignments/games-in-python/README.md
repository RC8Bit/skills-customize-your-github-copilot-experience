# 📘 Assignment: Hangman Game

## 🎯 Objective

Build the classic word-guessing game in Python, practising string manipulation, loops, conditionals, and random selection.

## 📝 Tasks

### 🛠️ Build the Hangman Game

#### Description
Create a Hangman game where the player guesses letters one at a time to reveal a hidden word before running out of attempts.

#### Requirements
Completed program should:

- Randomly select a word from a predefined list using the `random` module
- Display the current progress in `_ _ _` format, revealing correctly guessed letters
- Accept a single letter as input per turn and validate the guess
- Track and display the number of incorrect guesses remaining (start with 6 attempts)
- End the game when the word is fully guessed or all attempts are exhausted
- Display a win message showing the word when the player guesses correctly
- Display a lose message revealing the word when the player runs out of attempts
