export function rejectedSections(
  results: PromiseSettledResult<unknown>[],
  labels: string[],
): string[] {
  return results
    .map((result, index) => (result.status === "rejected" ? labels[index] : null))
    .filter((label): label is string => Boolean(label));
}
