import { OnboardingQuestionsForm } from "@/features/onboarding/ui/onboarding-questions-form";

export default function OnboardingQuestionsPage() {
  return (
    <main className="flex min-h-[100svh] justify-center px-4 py-6 min-[375px]:px-5 min-[375px]:py-8 sm:p-8">
      <OnboardingQuestionsForm />
    </main>
  );
}
