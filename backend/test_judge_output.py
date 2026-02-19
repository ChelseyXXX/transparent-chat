"""
Test Judge LLM output quality
"""
import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

from linguistic_calibration import analyze_response
import json

# Test case: A response with clear hedging
test_question = "What causes inflation?"

test_answer = """Inflation is generally caused by increased money supply, though I'm not entirely certain of all the mechanisms. There are probably multiple factors involved, like demand-pull inflation and maybe cost-push inflation. Some economists argue that fiscal policy plays a role, but the exact relationship seems complicated."""

test_reasoning = """Let me think about this... I recall learning about money supply and inflation, but I'm not 100% confident on all the details. There's the quantity theory of money (MV=PQ), which suggests that if money supply (M) increases faster than output, prices (P) rise. But wait, I should also consider demand-pull vs cost-push. Actually, I'm not sure if I'm covering all the modern theories here."""

print("=" * 60)
print("TESTING JUDGE LLM OUTPUT QUALITY")
print("=" * 60)

print("\n📝 Test Question:")
print(f"   {test_question}")

print("\n💬 Test Answer (with hedging):")
print(f"   {test_answer[:200]}...")

print("\n🧠 Test Reasoning (with self-correction):")
print(f"   {test_reasoning[:200]}...")

print("\n" + "=" * 60)
print("CALLING JUDGE LLM...")
print("=" * 60)

try:
    result = analyze_response(
        user_question=test_question,
        assistant_answer=test_answer,
        assistant_reasoning=test_reasoning
    )

    print("\n✅ Judge analysis completed!")
    print(f"\n📊 Confidence Level: {result['confidence_level'].upper()}")
    print(f"📈 Overall Uncertainty: {result['overall_uncertainty']:.2f}")
    print(f"📝 Summary: {result['summary']}")

    print(f"\n🔍 Markers Detected: {len(result.get('markers', []))}")

    if result.get('markers'):
        for idx, marker in enumerate(result['markers'], 1):
            print(f"\n{'─' * 60}")
            print(f"Marker #{idx}: {marker['dimension']} ({marker['severity'].upper()} {marker['type']})")
            print(f"{'─' * 60}")

            if marker.get('evidence'):
                print(f"\n📌 Evidence ({len(marker['evidence'])} quotes):")
                for i, quote in enumerate(marker['evidence'], 1):
                    print(f"   {i}. \"{quote}\"")

            if marker.get('interpretation'):
                print(f"\n💡 Interpretation ({len(marker['interpretation'])} chars):")
                print(f"   {marker['interpretation']}")

            if marker.get('user_guidance'):
                print(f"\n✓ User Guidance ({len(marker['user_guidance'])} chars):")
                print(f"   {marker['user_guidance']}")
    else:
        print("\n⚠️  WARNING: No markers detected!")
        print("   This suggests the Judge prompt may not be working correctly.")

    print("\n" + "=" * 60)
    print("FULL JSON OUTPUT:")
    print("=" * 60)
    print(json.dumps(result, indent=2, ensure_ascii=False))

except Exception as e:
    print(f"\n❌ ERROR: {e}")
    import traceback
    traceback.print_exc()
