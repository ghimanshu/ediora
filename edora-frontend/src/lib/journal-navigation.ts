export type JournalMenuItem = { slug: string; title: string; menu_group?: string };
export type JournalMenuEntry = { title: string; items: JournalMenuItem[]; grouped: boolean };
export function groupJournalMenu(items: JournalMenuItem[]): JournalMenuEntry[] {
  const entries: JournalMenuEntry[] = [];
  const groups = new Map<string, JournalMenuEntry>();
  for (const item of items) {
    const group = item.menu_group?.trim();
    if (!group) { entries.push({ title: item.title, items: [item], grouped: false }); continue; }
    let entry = groups.get(group);
    if (!entry) { entry = { title: group, items: [], grouped: true }; groups.set(group, entry); entries.push(entry); }
    entry.items.push(item);
  }
  return entries;
}
