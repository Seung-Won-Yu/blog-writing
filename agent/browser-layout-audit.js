// Read-only expression for tab.playwright.evaluate; never a visual-QA approval.
(() => {
  const tolerance = 2;
  const issues = [];
  const pending = [];
  const review = [];
  const scope = '.daily-digest-post, .daily-digest-continuation';
  const roots = [...document.querySelectorAll(scope)];
  const tableNodes = [...document.querySelectorAll(
    '.daily-digest-post table, .daily-digest-continuation table'
  )];
  const imageNodes = [...document.querySelectorAll(
    '.daily-digest-post img, .daily-digest-continuation img'
  )];
  const width = el => el.getBoundingClientRect().width;
  const round = n => Math.round(n * 100) / 100;
  const pageWidth = document.documentElement.clientWidth;
  if (!roots.length) issues.push('article_root_missing');
  if (roots.length && !imageNodes.length) issues.push('article_images_missing');
  if (document.documentElement.scrollWidth > pageWidth + tolerance) {
    issues.push('document_horizontal_overflow');
  }

  const tables = tableNodes.map((table, index) => {
    const id = `table_${index + 1}`;
    const tableWidth = width(table);
    const wrapper = table.closest('.digest-table-wrap');
    const columns = table.rows[0]?.cells.length || 0;
    const groups = [table.caption, table.tHead, ...table.tBodies, ...table.rows].filter(Boolean);
    if (!tableWidth || !table.rows.length) issues.push(`${id}:empty_layout`);
    if (groups.some(group => Math.abs(width(group) - tableWidth) > tolerance)) {
      issues.push(`${id}:inner_width_mismatch`);
    }
    const captionAlign = table.caption ? getComputedStyle(table.caption).textAlign : null;
    if (table.caption && !['left', 'start'].includes(captionAlign)) {
      issues.push(`${id}:caption_alignment`);
    }
    if (!wrapper) issues.push(`${id}:scroll_wrapper_missing`);
    else {
      if (columns <= 2 && Math.abs(tableWidth - wrapper.clientWidth) > tolerance) {
        issues.push(`${id}:compact_width_mismatch`);
      }
      if (tableWidth > wrapper.clientWidth + tolerance &&
          !['auto', 'scroll'].includes(getComputedStyle(wrapper).overflowX)) {
        issues.push(`${id}:uncontained_overflow`);
      }
    }
    return {
      id, columns, caption: table.caption?.textContent.trim() || '',
      wrapper: wrapper?.clientWidth ?? null, table: round(tableWidth),
      header: table.tHead ? round(width(table.tHead)) : null,
      bodies: [...table.tBodies].map(body => round(width(body))), captionAlign,
    };
  });

  const images = imageNodes.map((image, index) => {
    const id = `image_${index + 1}`;
    const rect = image.getBoundingClientRect();
    const style = getComputedStyle(image);
    const loaded = image.complete && image.naturalWidth > 0;
    if (!image.complete) pending.push(`${id}:load_pending_scroll_then_recheck`);
    else if (!image.naturalWidth) issues.push(`${id}:load_failed`);
    if (loaded && (!rect.width || !rect.height)) issues.push(`${id}:zero_size`);
    if (rect.left < -tolerance || rect.right > pageWidth + tolerance) {
      issues.push(`${id}:outside_reading_viewport`);
    }
    const ratioError = loaded && rect.height > 0
      ? Math.abs((rect.width / rect.height) / (image.naturalWidth / image.naturalHeight) - 1)
      : 0;
    if (ratioError > 0.03) {
      if (['fill', ''].includes(style.objectFit)) issues.push(`${id}:stretched_ratio`);
      else review.push(`${id}:fitted_or_cropped_box_review`);
    }
    const figure = image.closest('figure');
    const caption = figure?.querySelector('figcaption');
    if (caption && +getComputedStyle(caption).fontSize.replace(/px$/, '') < 12) {
      issues.push(`${id}:caption_too_small`);
    }
    return {
      id, alt: image.alt, loaded, natural: [image.naturalWidth, image.naturalHeight],
      rendered: [round(rect.width), round(rect.height)], objectFit: style.objectFit,
      ratioError: round(ratioError), caption: caption?.textContent.trim() || '',
    };
  });

  return {
    status: issues.length ? 'METRICS_FAIL' : pending.length ? 'IMAGES_PENDING' : 'METRICS_PASS',
    url: location.href, observedAt: new Date().toISOString(),
    viewport: [innerWidth, innerHeight], documentWidth: document.documentElement.scrollWidth,
    tables, images, issues, pending, review,
    note: '수치 검사는 시각 검수 승인이 아니다. 이미지 문자·잘림·캡션 연결·썸네일은 실제 화면에서 확인한다.',
  };
})()
