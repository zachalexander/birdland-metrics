export const environment = {
  production: true,
  contentful: {
    spaceId: 'btpj5jq8xkdj',
    accessToken: '4fhLNRRGeWU2PoYE9z32gVJcjHQ_YR83KCOxFPwN9rE',
    contentTypeIds: {
      blogPost: 'article',
      author: 'author',
      category: 'category',
    },
  },
  s3: {
    eloRatings: 'https://mlb-elo-ratings-output.s3.amazonaws.com',
    predictions: 'https://mlb-predictions-2026.s3.amazonaws.com',
  },
};
