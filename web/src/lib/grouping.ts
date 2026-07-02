import type { DocumentGroup, DocsIndexItem } from "./types";

const DAY_IN_MS = 24 * 60 * 60 * 1000;

export function groupByTime(
  documents: DocsIndexItem[],
  now: number = Date.now()
): DocumentGroup[] {
  const threeDaysAgo = now - 3 * DAY_IN_MS;
  const oneWeekAgo = now - 7 * DAY_IN_MS;
  const groups: DocumentGroup[] = [];

  const recentDocuments = sortByCreatedAtDesc(
    documents.filter((document) => getDocumentTimestamp(document) > threeDaysAgo)
  );
  const thisWeekDocuments = sortByCreatedAtDesc(
    documents.filter((document) => {
      const timestamp = getDocumentTimestamp(document);
      return timestamp > oneWeekAgo && timestamp <= threeDaysAgo;
    })
  );
  const olderDocuments = sortByCreatedAtDesc(
    documents.filter((document) => getDocumentTimestamp(document) <= oneWeekAgo)
  );

  if (recentDocuments.length > 0) {
    groups.push({
      id: "recent-3-days",
      label: "最近三天",
      icon: "calendar",
      documents: recentDocuments
    });
  }

  if (thisWeekDocuments.length > 0) {
    groups.push({
      id: "this-week",
      label: "本周",
      icon: "calendar",
      documents: thisWeekDocuments
    });
  }

  if (olderDocuments.length > 0) {
    groups.push({
      id: "older",
      label: "更早",
      icon: "calendar",
      documents: olderDocuments
    });
  }

  return groups;
}

export function groupByIndustry(documents: DocsIndexItem[]): DocumentGroup[] {
  const industryMap = new Map<string, DocsIndexItem[]>();

  for (const document of documents) {
    const industry = inferIndustry(document);
    const currentDocuments = industryMap.get(industry) ?? [];
    currentDocuments.push(document);
    industryMap.set(industry, currentDocuments);
  }

  return Array.from(industryMap.entries())
    .map(([industry, groupDocuments]) => ({
      id: `industry-${industry}`,
      label: industry,
      icon: getIndustryIcon(industry),
      documents: sortByCreatedAtDesc(groupDocuments)
    }))
    .sort((left, right) => {
      const countDiff = right.documents.length - left.documents.length;
      if (countDiff !== 0) {
        return countDiff;
      }
      return left.label.localeCompare(right.label, "zh-CN");
    });
}

export function formatDocumentDate(document: DocsIndexItem): string {
  const timestamp = getDocumentTimestamp(document);
  if (timestamp <= 0) {
    return "未知时间";
  }

  return new Date(timestamp).toLocaleDateString("zh-CN", {
    year: "numeric",
    month: "2-digit",
    day: "2-digit"
  });
}

export function getDocumentTimestamp(document: DocsIndexItem): number {
  const publishedAtTimestamp = getPublishedAtTimestamp(document.published_at);
  if (publishedAtTimestamp > 0) {
    return publishedAtTimestamp;
  }

  if (typeof document.created_at === "number" && Number.isFinite(document.created_at)) {
    return document.created_at;
  }

  const dateMatch = document.source_file.match(/^(\d{4})[-_/年](\d{1,2})[-_/月](\d{1,2})/);
  if (!dateMatch) {
    return 0;
  }

  const [, year, month, day] = dateMatch;
  return new Date(Number(year), Number(month) - 1, Number(day)).getTime();
}

function getPublishedAtTimestamp(publishedAt: string | null | undefined): number {
  if (!publishedAt) {
    return 0;
  }

  const dateMatch = publishedAt.match(/^(\d{4})-(\d{1,2})-(\d{1,2})$/);
  if (!dateMatch) {
    return 0;
  }

  const [, year, month, day] = dateMatch;
  return new Date(Number(year), Number(month) - 1, Number(day)).getTime();
}

function sortByCreatedAtDesc(documents: DocsIndexItem[]): DocsIndexItem[] {
  return [...documents].sort(
    (left, right) => getDocumentTimestamp(right) - getDocumentTimestamp(left)
  );
}

function inferIndustry(document: DocsIndexItem): string {
  if (document.industry && document.industry.trim()) {
    return document.industry.trim();
  }

  const haystack = [
    document.company_name,
    document.source_file,
    ...(document.tags ?? [])
  ].join(" ");

  if (/思必驰|人工智能|语音|大模型|智能|AI/i.test(haystack)) {
    return "人工智能";
  }
  if (/半导体|芯片|集成电路|晶圆|封装/.test(haystack)) {
    return "半导体";
  }
  if (/新能源|光伏|储能|风电|锂电/.test(haystack)) {
    return "新能源";
  }
  if (/医药|医疗|生物|制药/.test(haystack)) {
    return "医药";
  }
  if (/汽车|车载|新能源车|永励/.test(haystack)) {
    return "汽车";
  }
  if (/消费|食品|零售|服饰/.test(haystack)) {
    return "消费";
  }
  if (/金融|银行|证券|保险/.test(haystack)) {
    return "金融";
  }

  return "未分类";
}

function getIndustryIcon(industry: string): string {
  const iconMap: Record<string, string> = {
    人工智能: "bot",
    半导体: "cpu",
    新能源: "zap",
    医药: "pill",
    汽车: "car",
    消费: "shopping-bag",
    金融: "building",
    未分类: "folder"
  };

  return iconMap[industry] ?? "building";
}
