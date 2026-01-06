<template>
  <div>
    <div class="mb-3">
      <div
        :id="bannerPreviewId"
        class="d-flex align-items-center justify-content-center border border-secondary rounded bg-primary"
        style="min-height: 200px;"
      >
        <img
          v-if="bannerUrl"
          class="w-100 object-fit-contain bg-dark"
          :src="bannerUrl"
          alt="Game banner preview"
          style="max-height: 200px;"
        />
      </div>
    </div>

    <div class="mb-3">
      <InputLabel :for-id="bannerInputId" text="BANNER/IMAGE URL" />
      <TextInput
        :id="bannerInputId"
        v-model="bannerUrl"
        type="url"
        placeholder="https://example.com/image.jpg"
      />
      <small class="form-text text-white-50">
        Updating this URL will refresh the banner image preview above.
      </small>
    </div>

    <div class="mb-3">
      <InputLabel :for-id="nameInputId" text="GAME NAME" />
      <TextInput :id="nameInputId" v-model="gameName" placeholder="Enter game name" required />
    </div>

    <div class="mb-3">
      <InputLabel text="SAVE FILE LOCATIONS" />
      <div :id="containerId">
        <div
          v-for="(location, index) in saveLocations"
          :key="`location-${index}`"
          class="input-group mb-2 save-location-row"
        >
          <TextInput
            v-model="saveLocations[index]"
            input-class="save-location-input"
            placeholder="Enter save file location"
            required
          />
          <IconButton
            type="button"
            variant="outline-danger"
            size="sm"
            class="px-2 py-1 remove-btn"
            icon="fa-times"
            :class="{ 'd-none': saveLocations.length === 1 }"
            @click="removeLocation(index)"
          />
        </div>
      </div>
      <IconButton
        type="button"
        variant="outline-secondary"
        size="sm"
        class="text-white mt-2"
        icon="fa-plus"
        @click="addLocation"
      >
        Add Another Location
      </IconButton>
      <small class="form-text text-white-50 d-block mt-2">
        Add multiple save file locations if your game saves to different folders.
      </small>
    </div>
  </div>
</template>

<script setup lang="ts">
import IconButton from '@/components/atoms/IconButton.vue';
import InputLabel from '@/components/atoms/InputLabel.vue';
import TextInput from '@/components/atoms/TextInput.vue';

const props = defineProps({
  prefix: { type: String, default: 'game' }
});

const bannerUrl = defineModel<string>('bannerUrl', { default: '' });
const gameName = defineModel<string>('gameName', { default: '' });
const saveLocations = defineModel<string[]>('saveLocations', { default: () => [''] });

const bannerPreviewId = `${props.prefix}-banner-preview`;
const bannerInputId = `${props.prefix}-banner`;
const nameInputId = `${props.prefix}-name`;
const containerId = `${props.prefix}-save-locations`;

const addLocation = () => {
  saveLocations.value.push('');
};

const removeLocation = (index: number) => {
  if (saveLocations.value.length === 1) {
    return;
  }
  saveLocations.value.splice(index, 1);
};
</script>

<style scoped>
</style>
