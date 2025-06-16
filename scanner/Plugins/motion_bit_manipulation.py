# TODO: MOVE+ AND MOVE- REQUIRE SPECIAL commands
COMMAND_MAP = {
    "VELOCITY": "000111",
    "ACCELERATION":"001100",
    "POSITIONADJUST":"010000",
    "WAIT":"001000",
    "MOVE+":"000001",
    "MOVE-":"000001"  
}


def text_to_bin(split_text):
    
    binAxis = ""
    binCommand_ = ""
    decimalValue = None 

   
    for word in split_text:
        if word == "X":
            binAxis = "00"
            break
        elif word == "Y":
            binAxis = "01"
            break
        elif word == "Z":
            binAxis = "10"
            break
        elif word == "W":
            binAxis = "11"
            break
    
   
    for word in split_text:
        if word in COMMAND_MAP:
            binCommand_ = COMMAND_MAP[word]
            print(f"Found Command: {word} -> {binCommand_}")
            break

   
    for word in split_text:
        try:
            num = int(word)
           
            if 0 <= num <= 32767: 
                decimalValue = num
                break
            else:
                print(f"Warning: Numeric value {num} is out of expected range (0-32767).")
        except ValueError:
            pass 

    if not binAxis:
        print("Warning: Axis (X, Y, Z, W) not found. Using default '00'.")
        binAxis = "00"
    
    
    axis_command_base_binary = binAxis + binCommand_ # This will be 8 bits

    # Right-pad with zeros to make it 16 bits 
    high_word_binary = axis_command_base_binary.ljust(16, '0')

    print(f"\nHigh Word Binary (Axis+Command+8x'0'): '{high_word_binary}' (Length: {len(high_word_binary)})")

    
    high_word_hex = None
    try:
        high_word_hex = hex(int(high_word_binary, 2))
        high_word_hex = '0x' + high_word_hex[2:].zfill(4) 
    except ValueError as e:
        print(f"Error converting High Word binary '{high_word_binary}' to hex: {e}")

   
    low_word_hex = None
    if decimalValue is not None:
        value_binary_str = bin(decimalValue)[2:]
        
        # Left-pad
        low_word_binary = value_binary_str.zfill(16)

        print(f"Low Word Binary (Value padded to 16 bits): '{low_word_binary}' (Length: {len(low_word_binary)})")

        try:
            low_word_hex = hex(int(low_word_binary, 2))
            
            low_word_hex = '0x' + low_word_hex[2:].zfill(4) 
        except ValueError as e:
            print(f"Error converting Low Word binary '{low_word_binary}' to hex: {e}")
    else:
        print("Warning: Numeric value not found for Low Word. Setting to default '0x0000'.")
        low_word_hex = "0x0000" # Default 16-bit hex zero

    # --- Function Output ---
    print(f"\n--- Final Output ---")
    print(f"High Word (Hex): {high_word_hex}")
    print(f"Low Word (Hex): {low_word_hex}")
    
    return {"high_word": high_word_hex, "low_word": low_word_hex}
 
    

MAX_SENTENCE_LENGTH = 100 

print("Enter sentence: ")

user_input = input()


if len(user_input) > MAX_SENTENCE_LENGTH:
    
    print(f"Error: Sentence is too long. Please limit your sentence to {MAX_SENTENCE_LENGTH} characters.")
else:
  
    user_input_upper = user_input.upper()


    user_input_words_split = user_input_upper.split()

  
    print(f"{user_input_words_split}")
    
    hex_word = text_to_bin(user_input_words_split)
    print(hex_word)




    