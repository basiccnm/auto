module.exports = function (eleventyConfig) {
  eleventyConfig.addFilter("comma", (num) => {
    if (num === null || num === undefined) return "";
    return Number(num).toLocaleString("ko-KR");
  });

  eleventyConfig.addFilter("onlyOpen", (items) => items.filter((i) => i.is_open));

  eleventyConfig.addFilter("relatedAcademies", (academies, current, limit = 5) => {
    return academies
      .filter(
        (a) =>
          a.sigungu === current.sigungu &&
          a.category_slug === current.category_slug &&
          a.slug !== current.slug
      )
      .slice(0, limit);
  });

  eleventyConfig.addPassthroughCopy({ "src/robots.txt": "robots.txt" });

  return {
    dir: {
      input: "src",
      output: "_site",
    },
  };
};
