import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import client from './client'
import type { Stats, Article, Finding, Contact, Source, Report, PaginatedResponse } from '../types'

export function useStats() {
  return useQuery<Stats>({
    queryKey: ['stats'],
    queryFn: async () => (await client.get('/stats')).data,
  })
}

export function useArticles(params: { page?: number; page_size?: number; country?: string } = {}) {
  return useQuery<PaginatedResponse<Article>>({
    queryKey: ['articles', params],
    queryFn: async () => (await client.get('/articles', { params })).data,
  })
}

export function useFindings(params: { page?: number; page_size?: number; priority?: string; agent?: string; status?: string } = {}) {
  return useQuery<PaginatedResponse<Finding>>({
    queryKey: ['findings', params],
    queryFn: async () => (await client.get('/findings', { params })).data,
  })
}

export function useContacts(params: { page?: number; page_size?: number; organisation_type?: string; min_influence?: number } = {}) {
  return useQuery<PaginatedResponse<Contact>>({
    queryKey: ['contacts', params],
    queryFn: async () => (await client.get('/contacts', { params })).data,
  })
}

export function useSources(params: { page?: number; page_size?: number } = {}) {
  return useQuery<PaginatedResponse<Source>>({
    queryKey: ['sources', params],
    queryFn: async () => (await client.get('/sources', { params })).data,
  })
}

export function useApproveSource() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (id: string) => client.post(`/sources/${id}/approve`),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['sources'] }),
  })
}

export function useRejectSource() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (id: string) => client.post(`/sources/${id}/reject`),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['sources'] }),
  })
}

export function useReports(params: { page?: number; page_size?: number; report_type?: string } = {}) {
  return useQuery<PaginatedResponse<Report>>({
    queryKey: ['reports', params],
    queryFn: async () => (await client.get('/reports', { params })).data,
  })
}
