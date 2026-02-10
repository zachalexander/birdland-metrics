// Development environment - replace with your own values for local dev
// Production builds use environment.prod.ts (via fileReplacements in angular.json)
export const environment = {
  production: false,
  contentful: {
    spaceId: 'YOUR_SPACE_ID',
    accessToken: 'YOUR_ACCESS_TOKEN',
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
