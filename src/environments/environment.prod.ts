export const environment = {
  production: true,
  contentful: {
    spaceId: process.env['CONTENTFUL_SPACE_ID'] ?? '',
    accessToken: process.env['CONTENTFUL_ACCESS_TOKEN'] ?? '',
    contentTypeIds: {
      blogPost: 'article',
      author: 'author',
      category: 'category',
    },
  },
};
