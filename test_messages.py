from classifier import classify_client_message


test_messages = [
    "Can you please send me my latest investment statement?",

    "When is my next review meeting?",

    "Markets are crashing. Should I sell all my investments and move to cash?",

    "I need to withdraw R50,000 from my investment as soon as possible.",

    "Can you please change my residential address on my profile?",

    "My husband passed away yesterday. I need help with his life insurance policy.",

    "I haven't received my tax certificate yet. Can you send it to me?",

    "Do you think I should move my retirement annuity into a more aggressive fund?",

    "Please increase my monthly debit order from R3,000 to R4,000.",

    "I've emailed three times and nobody has responded. I'm extremely unhappy.",

    "Can you send me the form I need to update my beneficiaries?",

    "I received a strange email claiming to be from my investment provider. Is it legitimate?",

    "I want to invest another R100,000. Where should I put it?",

    "Can we move our meeting from Tuesday to Thursday?",

    "I urgently need money for a medical emergency. How quickly can I access my investment?",

    "What documents do you still need from me?",

    "My debit order went off twice this month. Please investigate.",

    "The market fell sharply today. Has anything happened to my portfolio?",

    "Please sell R100,000 of my investment today.",

    "Just confirming that I've uploaded the documents you requested."
]


for number, message in enumerate(test_messages, start=1):

    print("\n" + "=" * 70)
    print(f"TEST {number}")
    print("=" * 70)

    print(f"\nCLIENT:\n{message}")

    result = classify_client_message(message)

    print(f"\nCategory:       {result.category}")
    print(f"Urgency:        {result.urgency}")
    print(f"Requires human: {result.requires_human}")
    print(f"Reason:         {result.reason}")
    print(f"Action:         {result.recommended_action}")