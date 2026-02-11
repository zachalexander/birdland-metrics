import { Document } from '@contentful/rich-text-types';

export interface BlogPost {
  title: string;
  slug: string;
  excerpt: string;
  content: Document;
  coverImage?: {
    url: string;
    title: string;
    width: number;
    height: number;
  };
  publishedAt: string;
  isPremium: boolean;
  featured: boolean;
  readingTime: number;
  tags: string[];
  author?: Author;
}

export interface Author {
  name: string;
  bio: string;
  avatar?: {
    url: string;
    title: string;
  };
}
