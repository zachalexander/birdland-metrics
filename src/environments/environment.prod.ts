export const environment = {
  production: true,
  contentful: {
    spaceId: process.env['CONTENTFUL_SPACE_ID'] ?? '',
    accessToken: process.env['CONTENTFUL_ACCESS_TOKEN'] ?? '',
    contentTypeIds: {
      blogPost: 'blogPost',
      author: 'author',
      category: 'category',
    },
  },
};
