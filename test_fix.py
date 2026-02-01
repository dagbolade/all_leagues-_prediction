# test_fix.py - Quick test for the syntax fix

print("🧪 Testing the syntax fix...")

try:
    # Test the fixed import
    from footy.intelligent_feature_selector import IntelligentFeatureSelector
    print("✅ Import successful")

    # Test the class initialization
    selector = IntelligentFeatureSelector()
    print("✅ Class initialization successful")

    print("🎉 Fix verified! The syntax error is resolved.")
    print("💡 You can now run: python main.py")

except Exception as e:
    print(f"❌ Still an issue: {e}")
    print("🔍 Let me know the exact error message")