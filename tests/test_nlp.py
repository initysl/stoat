from stoat.core.nlp_engine import NLPEngine

def test_basic_commands():
    engine = NLPEngine()
    
    test_commands = [
        "open firefox",
        "find my resume",
        "move all PDFs from Downloads to Documents",
        "close chrome",
        "delete old files",
    ]
    
    for command in test_commands:
        print(f"\n{'='*60}")
        print(f"Command: {command}")
        try:
            intent = engine.parse_intent(command)
            print(f" Get in jorr {intent.to_summary()}")
        except Exception as e:
            print(f" Error fahhhhh: {e}")

if __name__ == "__main__":
    test_basic_commands()