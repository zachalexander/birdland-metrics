import { Injectable } from '@angular/core';
import { createClient, ContentfulClientApi, Entry } from 'contentful';
import { environment } from '../../../environments/environment';
import { Author, BlogPost } from '../../shared/models/content.models';

@Injectable({ providedIn: 'root' })
export class ContentfulService {
  private client: ContentfulClientApi<undefined>;

  constructor() {
    this.client = createClient({
      space: environment.contentful.spaceId,
      accessToken: environment.contentful.accessToken,
    });
  }

  async getArticles(limit = 10, skip = 0): Promise<BlogPost[]> {
    const entries = await this.client.getEntries({
      content_type: environment.contentful.contentTypeIds.blogPost,
      order: ['-sys.createdAt'],
      limit,
      skip,
    });
    return entries.items.map((entry) => this.mapBlogPost(entry));
  }

  async getArticleBySlug(slug: string): Promise<BlogPost | null> {
    const entries = await this.client.getEntries({
      content_type: environment.contentful.contentTypeIds.blogPost,
      'fields.slug': slug,
      limit: 1,
    });
    if (entries.items.length === 0) return null;
    return this.mapBlogPost(entries.items[0]);
  }

  async getArticlesByCategory(category: string): Promise<BlogPost[]> {
    const entries = await this.client.getEntries({
      content_type: environment.contentful.contentTypeIds.blogPost,
      'fields.tags[in]': category,
      order: ['-sys.createdAt'],
    });
    return entries.items.map((entry) => this.mapBlogPost(entry));
  }

  async getCategories(): Promise<string[]> {
    const entries = await this.client.getEntries({
      content_type: environment.contentful.contentTypeIds.blogPost,
      select: ['fields.tags'],
    });
    const tags = entries.items.flatMap(
      (entry) => ((entry.fields as Record<string, unknown>)['tags'] as string[]) ?? []
    );
    return [...new Set(tags)];
  }

  private mapBlogPost(entry: Entry): BlogPost {
    const fields = entry.fields as Record<string, unknown>;
    const imageEntry = fields['coverImage'] as Entry | undefined;
    const imageFile = imageEntry
      ? (imageEntry.fields as Record<string, unknown>)['file'] as Record<string, unknown> | undefined
      : undefined;
    const imageDetails = imageFile?.['details'] as Record<string, unknown> | undefined;
    const imageSize = imageDetails?.['image'] as Record<string, unknown> | undefined;

    const authorEntry = fields['author'] as Entry | undefined;
    const author = authorEntry ? this.mapAuthor(authorEntry) : undefined;

    return {
      title: fields['title'] as string,
      slug: fields['slug'] as string,
      excerpt: (fields['excerpt'] as string) ?? '',
      content: fields['content'] as BlogPost['content'],
      coverImage: imageFile
        ? {
            url: `https:${imageFile['url'] as string}`,
            title: (imageEntry!.fields as Record<string, unknown>)['title'] as string,
            width: (imageSize?.['width'] as number) ?? 800,
            height: (imageSize?.['height'] as number) ?? 450,
          }
        : undefined,
      publishedAt: (fields['publishedAt'] as string) ?? entry.sys.createdAt,
      isPremium: (fields['isPremium'] as boolean) ?? false,
      featured: (fields['featured'] as boolean) ?? false,
      tags: (fields['tags'] as string[]) ?? [],
      author,
    };
  }

  private mapAuthor(entry: Entry): Author {
    const fields = entry.fields as Record<string, unknown>;
    const avatarEntry = fields['avatar'] as Entry | undefined;
    const avatarFile = avatarEntry
      ? (avatarEntry.fields as Record<string, unknown>)['file'] as Record<string, unknown> | undefined
      : undefined;

    return {
      name: fields['name'] as string,
      bio: (fields['bio'] as string) ?? '',
      avatar: avatarFile
        ? {
            url: `https:${avatarFile['url'] as string}`,
            title: (avatarEntry!.fields as Record<string, unknown>)['title'] as string,
          }
        : undefined,
    };
  }
}
