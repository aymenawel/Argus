// Model ids in the words a person reads: "meta-models/muse-spark-open-1026" is Muse Spark Open, Meta's open-weight
// model on Baseten (D-77); the rest are named by their id.
const NAMES: [RegExp, string][] = [[/^meta-models\/muse-spark-open/, "Muse Spark Open"]];

export function modelName(id: string | null | undefined): string {
  if (!id) return "";
  const known = NAMES.find(([pattern]) => pattern.test(id));
  if (known) return known[1];
  return id
    .replace(/^.*\//, "")
    .split("-")
    .map((word) => (word === "sam" ? "SAM" : word.charAt(0).toUpperCase() + word.slice(1)))
    .join(" ");
}
