export function publicProductUrl(url) {
  if (!url) return "";
  try {
    const parsed = new URL(url);
    if (["example.com", "www.example.com"].includes(parsed.hostname)) return "";
    if (!["http:", "https:"].includes(parsed.protocol)) return "";
    return parsed.toString();
  } catch {
    return "";
  }
}

export function openPublicProductUrl(url) {
  const publicUrl = publicProductUrl(url);
  if (!publicUrl) return false;
  window.open(publicUrl, "_blank", "noopener,noreferrer");
  return true;
}

export const PRODUCT_LINK_UNAVAILABLE_TEXT = "公开 Demo 暂无真实下单链接";
