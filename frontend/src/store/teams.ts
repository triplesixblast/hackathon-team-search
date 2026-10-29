import { defineStore } from 'pinia';
import { ref } from 'vue';
import apiClient from '../utils/api';

export const useTeamsStore = defineStore('teams', () => {
  const teams = ref<any[]>([]);
  const currentTeam = ref<any>(null);
  const loading = ref(false);
  const error = ref('');

  async function fetchTeamsByHackathon(hackathonId: number, statusFilter: string = 'open') {
    loading.value = true;
    error.value = '';
    try {
      const response = await apiClient.get(`/api/teams/hackathons/${hackathonId}`, {
        params: { status_filter: statusFilter },
      });
      teams.value = response.data;
      return response.data;
    } catch (e: any) {
      error.value = e?.response?.data?.detail || e?.message || 'Ошибка загрузки команд';
      throw e;
    } finally {
      loading.value = false;
    }
  }

  async function fetchTeam(teamId: number) {
    loading.value = true;
    error.value = '';
    try {
      const response = await apiClient.get(`/api/teams/${teamId}`);
      currentTeam.value = response.data;
      return response.data;
    } catch (e: any) {
      error.value = e?.response?.data?.detail || e?.message || 'Ошибка загрузки команды';
      throw e;
    } finally {
      loading.value = false;
    }
  }

  async function createTeam(data: { hackathon_id: number; name: string; description?: string }) {
    loading.value = true;
    error.value = '';
    try {
      const response = await apiClient.post('/api/teams', data);
      teams.value.push(response.data);
      return response.data;
    } catch (e: any) {
      error.value = e?.response?.data?.detail || e?.message || 'Ошибка создания команды';
      throw e;
    } finally {
      loading.value = false;
    }
  }

  async function inviteUser(teamId: number, userId: number) {
    loading.value = true;
    error.value = '';
    try {
      await apiClient.post(`/api/teams/${teamId}/invite`, null, {
        params: { user_id: userId },
      });
      return true;
    } catch (e: any) {
      error.value = e?.response?.data?.detail || e?.message || 'Ошибка отправки приглашения';
      throw e;
    } finally {
      loading.value = false;
    }
  }

  async function removeMember(teamId: number, userId: number) {
    loading.value = true;
    error.value = '';
    try {
      await apiClient.delete(`/api/teams/${teamId}/members/${userId}`);
      // Обновляем текущую команду
      if (currentTeam.value?.id === teamId) {
        await fetchTeam(teamId);
      }
      return true;
    } catch (e: any) {
      error.value = e?.response?.data?.detail || e?.message || 'Ошибка удаления участника';
      throw e;
    } finally {
      loading.value = false;
    }
  }

  function clearTeams() {
    teams.value = [];
    currentTeam.value = null;
    error.value = '';
  }

  return {
    teams,
    currentTeam,
    loading,
    error,
    fetchTeamsByHackathon,
    fetchTeam,
    createTeam,
    inviteUser,
    removeMember,
    clearTeams,
  };
});

