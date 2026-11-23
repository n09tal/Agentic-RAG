import { BackendStatus } from "@/components/backend-status";

export default function Home() {
  return (
    <main className="mx-auto flex w-full max-w-2xl flex-1 flex-col gap-4 px-6 py-24">
      <h1 className="text-3xl font-semibold">Amazon Review Analysis Assistant</h1>
      <p className="text-zinc-600 dark:text-zinc-400">
        Ask questions about headphones and get answers backed by real Amazon reviews.
      </p>
      <BackendStatus />
    </main>
  );
}