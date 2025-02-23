import re
import streamlit as st
from phi.agent import Agent
from phi.model.openai import OpenAIChat

# Initialize session state variables
if 'wallet' not in st.session_state:
    st.session_state.wallet = 100
if 'game_in_progress' not in st.session_state:
    st.session_state.game_in_progress = False
if 'choice' not in st.session_state:
    st.session_state.choice = None

# Streamlit App Title
st.title("🎮 Agent X vs Agent O: Tic-Tac-Toe Game")

with st.chat_message("assistant"):
    st.markdown("""
        **Welcome to the Tic-Tac-Toe AI Battle!**   
        This project pits two advanced AI against AI 
    """)
    st.info("""
        "Player X and Player O play against each other. The judge judges any illegal move and tells if it's a draw or a win",
        "All the players are powered by OpenAI"
    """)
    st.markdown("Place your bets , and lets see who wins")

# Function to display the board with better styling
def display_board(board):
    st.markdown("""
        <style>
        .board {
            display: grid;
            grid-template-columns: repeat(3, 50px);
            grid-template-rows: repeat(3, 50px);
            gap: 5px;
            margin-bottom: 20px;
        }
        .cell {
            display: flex;
            align-items: center;
            justify-content: center;
            border: 1px solid #ccc;
            font-size: 20px;
            font-weight: bold;
        }
        </style>
    """, unsafe_allow_html=True)

    st.write("Current Board:")
    board_html = '<div class="board">'
    for row in board:
        for cell in row:
            cell_value = cell if cell is not None else "&nbsp;"
            board_html += f'<div class="cell">{cell_value}</div>'
    board_html += '</div>'
    st.markdown(board_html, unsafe_allow_html=True)

def get_board_state(board):
    rows = []
    for i, row in enumerate(board):
        row_str = " | ".join([f"({i},{j}) {cell or ' '}" for j, cell in enumerate(row)])
        rows.append(f"Row {i}: {row_str}")
    return "\n".join(rows)

def check_winner(board):
    # Check rows
    for row in board:
        if row[0] == row[1] == row[2] and row[0] is not None:
            return row[0]
    # Check columns
    for col in range(3):
        if board[0][col] == board[1][col] == board[2][col] and board[0][col] is not None:
            return board[0][col]
    # Check diagonals
    if board[0][0] == board[1][1] == board[2][2] and board[0][0] is not None:
        return board[0][0]
    if board[0][2] == board[1][1] == board[2][0] and board[0][2] is not None:
        return board[0][2]
    # Check for draw
    if all(cell is not None for row in board for cell in row):
        return "Draw"
    return None

# Sidebar for API keys and wallet display
st.sidebar.header("API Keys")
openai_api_key = st.sidebar.text_input("Enter your OpenAI API Key", type="password")
if openai_api_key:
    st.session_state.openai_api_key = openai_api_key


st.sidebar.info(f"Current Wallet Balance: {st.session_state.wallet:.2f}")

# betting options 
if not st.session_state.game_in_progress:
    Amount = st.sidebar.number_input("Enter your bet amount", 
                                   min_value=2.0, 
                                   max_value=float(st.session_state.wallet),
                                   step=1.0, 
                                   value=None, 
                                   format="%.2f")
    
    if Amount is not None:
        st.sidebar.write("### Choose X or O:")
        col1, col2 = st.sidebar.columns(2)
        
        if col1.button("X"):
            st.session_state.choice = "X"
            st.session_state.bet_amount = Amount
        
        if col2.button("O"):
            st.session_state.choice = "O"
            st.session_state.bet_amount = Amount
        
        if st.session_state.choice:
            st.sidebar.success(f"Your choice: {st.session_state.choice}")
            st.sidebar.info(f"Bet amount: ${Amount:.2f}")

# Initialize agents if API key is provided
if 'openai_api_key' in st.session_state:
    player_x = Agent(
        name="Player X",
        model=OpenAIChat(id="gpt-4o", temperature=0.1, api_key=st.session_state.openai_api_key),
        instructions=[
            "You are a Tic-Tac-Toe player using the symbol 'X'.",

            "Your opponent is using the symbol 'O'. Block their potential winning moves.",
            "Make your move in the format 'row, col' based on the current board state.",
            "Strategize to win by placing your symbol in a way that blocks your opponent from forming a straight line.",
            "Do not include any explanations or extra text. Only provide the move.",
            "Don't play where the other player has already played",
            "Row and column indices start from 0.",
        ],
        markdown=True,
    )

    player_o = Agent(
        name="Player O",
        model=OpenAIChat(id="gpt-4o", temperature=0.1, api_key=st.session_state.openai_api_key),
        instructions=[
            "You are a Tic-Tac-Toe player using the symbol 'O'.",
            "Your opponent is using the symbol 'X'. Block their potential winning moves.",
            "Make your move in the format 'row, col' based on the current board state.",
            "Strategize to win by placing your symbol in a way that blocks your opponent from forming a straight line.",
            "Do not include any explanations or extra text. Only provide the move.",
            "Row and column indices start from 0.",
        ],
        markdown=True,
    )

    judge = Agent(
        name="Judge",
        model=OpenAIChat(id="gpt-4o", temperature=0.1, api_key=st.session_state.openai_api_key),
        instructions=[
            "You are the judge of a Tic-Tac-Toe game.",
            "The board is presented as rows with positions separated by '|'.",
            "Rows are labeled from 0 to 2, and columns from 0 to 2.",
            "Determine the winner based on this board state.",
            "The winner is the player with three of their symbols in a straight line (row, column, or diagonal).",
            "If the board is full and there is no winner, declare a draw.",
            "Provide only the result (e.g., 'Player X wins', 'Player O wins', 'Draw').",
        ],
        markdown=True,
    )

    def extract_move(response):
        content = response.content.strip()
        match = re.search(r'\d\s*,\s*\d', content)
        if match:
            move = match.group().replace(' ', '')
            return move
        numbers = re.findall(r'\d+', content)
        if len(numbers) >= 2:
            row = int(numbers[0])
            col = int(numbers[1])
            return f"{row},{col}"
        return None

    def play_game():
        st.session_state.game_in_progress = True
        
        if 'board' not in st.session_state:
            st.session_state.board = [[None, None, None],
                                    [None, None, None],
                                    [None, None, None]]
        if 'current_player' not in st.session_state:
            st.session_state.current_player = player_x
        if 'symbol' not in st.session_state:
            st.session_state.symbol = "X"
        if 'move_count' not in st.session_state:
            st.session_state.move_count = 0

        max_moves = 9
        winner = None

        while st.session_state.move_count < max_moves:
            st.write("**Current Board:**")
            display_board(st.session_state.board)

            board_state = get_board_state(st.session_state.board)
            move_prompt = (
                f"Current board state:\n{board_state}\n"
                f"{st.session_state.current_player.name}'s turn. Provide your move in 'row, col' format."
            )

            st.write(f"**{st.session_state.current_player.name}'s turn:**")
            move_response = st.session_state.current_player.run(move_prompt)
            st.write(f"Agent Response: {move_response.content}")
            move = extract_move(move_response)

            if not move:
                st.error("Invalid move! Please use the format 'row, col'.")
                continue

            try:
                row, col = map(int, move.split(','))
                if st.session_state.board[row][col] is not None:
                    st.error("That cell is already occupied. Try again.")
                    continue
                st.session_state.board[row][col] = st.session_state.symbol
            except (ValueError, IndexError):
                st.error("Invalid move! Please provide row and column numbers like '1, 2'.")
                continue

            winner = check_winner(st.session_state.board)
            if winner:
                break

            if st.session_state.current_player == player_x:
                st.session_state.current_player = player_o
                st.session_state.symbol = "O"
            else:
                st.session_state.current_player = player_x
                st.session_state.symbol = "X"

            st.session_state.move_count += 1

        st.write("**Final Board:**")
        display_board(st.session_state.board)

        # Update wallet based on game outcome
        if winner:
            if winner == st.session_state.choice:
                st.session_state.wallet += st.session_state.bet_amount
                st.success(f"Congratulations! {winner} wins! You won ${st.session_state.bet_amount:.2f}")
            else:
                st.session_state.wallet -= st.session_state.bet_amount
                st.error(f"Game Over! {winner} wins! You lost ${st.session_state.bet_amount:.2f}")
        else:
            st.success("**Result:** It's a draw!")

       
        st.info(f"Your new wallet balance: ${st.session_state.wallet:.2f}")
        st.write("**The judge is evaluating the game result...**")
        final_board_state = get_board_state(st.session_state.board)
        judge_prompt = (
            f"Final board state:\n{final_board_state}\n"
            "Determine the winner and provide the result."
        )
        judge_response = judge.run(judge_prompt)
        st.write("**Judge's Response:**")
        st.code(judge_response.content)

        # Reset game state
        st.session_state.game_in_progress = False
        st.session_state.choice = None
        if 'bet_amount' in st.session_state:
            del st.session_state.bet_amount

  
    if not st.session_state.game_in_progress and st.session_state.choice and 'bet_amount' in st.session_state:
        if st.button("Start Game"):
            st.session_state.board = [[None, None, None],
                                    [None, None, None],
                                    [None, None, None]]
            st.session_state.current_player = player_x
            st.session_state.symbol = "X"
            st.session_state.move_count = 0
            play_game()
else:
    st.warning("Please enter your OpenAI API key to start the game.")