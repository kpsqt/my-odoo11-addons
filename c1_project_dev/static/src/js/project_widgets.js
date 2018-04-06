odoo.define('web.c1_project_dev', function (require) {
    "use strict";

    var core = require('web.core');
    // var formats = require('web.formats');
    // var Priority = require('web.Priority');
    // var form_common = require('web.form_common');

    var dialogs = require('web.view_dialogs');

    // var ProgressBar = require('web.ProgressBar');
    var pyeval = require('web.pyeval');
    var Registry = require('web.Registry');
    var session = require('web.session');
    var Widget = require('web.Widget');
    var data = require('web.data');
    var QWeb = core.qweb;
    var _t = core._t;
    // var Model = require('web.DataModel');
    var rpc = require('web.rpc');
    var FormView = require('web.FormView');
    var widgetRegistry = require('web.widget_registry');
    var FieldManagerMixin = require('web.FieldManagerMixin');


    var ModuleReviewListDialog = Widget.extend({
        events: {
            'hidden.bs.modal': 'destroy',
        },
        template: 'c1_project_dev.ModuleReviewListDialog',
        init: function (module_id) {
            // this._super(parent);
            // console.log(parent);
            // console.log(object);
            this.module_id = module_id;
            return this._super.apply(this, arguments);
        },
        start: function () {
            console.log(this.module_id.name);
            // this.$el.find('h3.modal-title').text(this.module_id.name);
            this.$el.modal();
        },
    });

    var ModuleRevisionMarkFormWidget = Widget.extend(FieldManagerMixin, {
        init: function (parent, object, state) {
            this._super(parent);
            FieldManagerMixin.init.call(this);
            this.data = object.data;
            this.mode = parent.mode || 'readonly';
        },
        events: {
            'click button.ct_composer_button_uprate': "up_rate",
            'click button.ct_composer_button_downrate': "down_rate",
            'click a.ct_mark_link': "display_composer",
            'click a.ct_see_all_mark_link': "display_revision_dialog",
            'click a.ct_composer_cancel_link': "hide_composer",
        },
        start: function () {
            if (this.data.module_id == false) {
                return;
            }
            console.log(this.data.module_id.data.id);
            var self = this;
            if (self.mode == 'readonly') {
                this._rpc({
                    model: 'c1_project_dev.module.review',
                    method: 'get_last_review',
                    args: [this.data.module_id.data.id],
                }).then(function (last_review) {
                    // console.log(last_review);
                    self.display_widget(last_review);
                });
            }

        },
        display_widget: function (last_review) {
            this.$el.html(QWeb.render("ModuleRevisionMarkFormWidget", {
                'reviews': last_review, // 'avatar_url': '/web/image/res.partner/' + last_review.user.partner_id + '/image_small',
            }));
            this.$('.ct_composer_container').hide();
        },
        up_rate: function () {
            var self = this;
            var comment = self.$('.o_composer_text_field').val();
            this._rpc({
                model: 'c1_project_dev.module.review',
                method: 'rate',
                args: [this.data.module_id.data.id, this.data.current_downloaded_rev, 'good', comment],
            }).then(function (res) {
                if (_.isEmpty(res)) {
                    // self.$('.o_hr_attendance_employee').append(_t("Error : Could not find employee linked to user"));
                    return;
                }
                // console.log(res);
                self.$('.o_composer_text_field').val('');
                self.$('.ct_composer_container').slideUp();
                self.restart();
            });
        },
        down_rate: function () {
            var self = this;
            var comment = self.$('.o_composer_text_field').val();
            this._rpc({
                model: 'c1_project_dev.module.review',
                method: 'rate',
                args: [this.data.module_id.data.id, this.data.current_downloaded_rev, 'not_good', comment],
            }).then(function (res) {
                if (_.isEmpty(res)) {
                    return;
                }
                // console.log(res);
                self.$('.o_composer_text_field').val('');
                self.$('.ct_composer_container').slideUp();
                self.restart();
            });
        },
        display_composer: function () {
            var self = this;
            // console.log(this.data.current_downloaded_rev);
            self.$('.ct_composer_container').slideDown();
            self.$('.o_composer_text_field').attr('placeholder', 'Comment revision ' + this.data.current_downloaded_rev);
        },
        hide_composer: function () {
            var self = this;
            self.$('.o_composer_text_field').val('');
            self.$('.ct_composer_container').slideUp();
        },
        restart: function () {
            var self = this;
            self.$el.empty();
            self.start();
        },
        display_revision_dialog: function () {
            var dialog = new ModuleReviewListDialog(this.data.module_id);
            var self = this;
            this._rpc({
                model: 'c1_project_dev.module.review',
                method: 'get_reviews',
                args: [self.data.module_id.data.id],
            }).then(function (res) {
                dialog.$el.find('.o_mail_thread').empty().append(QWeb.render('review_list', {
                    'reviews': res,
                }));
                dialog.$el.find('.modal-title').empty().append(self.data.module_id.data.display_name+'');
            });
            dialog.appendTo($(document.body));
        }
    });

    /*core.form_custom_registry.add(
     'module_revision_marker', ModuleRevisionMarkFormWidget
     );*/
    widgetRegistry.add('module_revision_marker', ModuleRevisionMarkFormWidget);


    // var ModulesFilter = form_common.FormWidget.extend({
    var ModulesFilter = Widget.extend(FieldManagerMixin, {
        // template: "RemoteDatabaseModuleFilter",
        init: function (parent, object) {
            this._super(parent);
            FieldManagerMixin.init.call(this);
            // console.log('INIT!!!');
            // console.log(object);
            this.data = object.data;

            // this._super.apply(this, arguments);
        },
        start: function () {
            this.display_filter();
        },
        events: {
            "click .ct_button_filter": "open_search_dialog",
        },
        open_search_dialog: function () {
            var self = this;
            console.log(self.data.id);
            new dialogs.SelectCreateDialog(this, _.extend({}, (this.options || {}), {
                res_model: 'c1_project_dev.module.info',
                domain: [['database_id', '=', self.data.id]],
                context: {},
                title: _t("Search modules in ") + self.data.name,
                disable_multiple_selection: true,
                on_selected: function (element_ids) {
                    console.log(element_ids);
                },
                no_create: true
            })).open();
        },
        display_filter: function () {
            this.$el.html(QWeb.render("RemoteDatabaseModuleFilter", {}));
        },
    });

    core.form_custom_registry.add(
        'remote_db_module_filter', ModulesFilter
    );

    widgetRegistry.add('remote_db_module_filter', ModulesFilter);


    var UserDataPathExplorer = Widget.extend({
        // template: 'UserDataPathExplorer',
        folder_list: [],
        events: {
            'click .folder-item': 'selected_item',
            'click button.del_button': 'delete_item',
            'click .btn-delete-folder': 'delete_folder',
            // 'click thead th.o_column_sortable[data-p]': 'sort_records',
        },
        start: function () {
            var self = this;
            rpc.query({
                model: "res.users",
                method: "get_users_backupspath_content",
                args: [],
            }).then(function (result) {
                self.folder_list = result;
                self.display_widget(self.folder_list);
            });
        },
        display_widget: function (folder_list) {
            var self = this;
            self.$el.append(QWeb.render('UserDataPathExplorer', {'folders': folder_list}));
            self.init_display();
        },
        selected_item: function (event) {
            var self = this;
            // console.log( self.folder_list[parseInt($(event.currentTarget).data('idx'), 10)] );
            var folder = self.folder_list[parseInt($(event.currentTarget).data('idx'), 10)];
            // var Users = new Model('res.users');

            rpc.query({
                model: "res.users",
                method: "get_backupspath_subfolder_content",
                args: [folder, true],
            }).then(function (result) {
                // console.log(result);
                self.$el.find('.folder-content-list-group').empty().append(QWeb.render('UserDataPathExplorer_FileTable', {
                    'file_list': result,
                    'folder': parseInt($(event.currentTarget).data('idx'), 10),
                    'current_folder': folder
                }));


            });
        },
        delete_item: function (event) {
            var self = this;
            var sub_folder = self.folder_list[parseInt($(event.currentTarget).data('p'), 10)];
            var file_name = $(event.currentTarget).data('name');

            var r = confirm('Do you really want to delete ' + sub_folder + '/' + file_name);
            if (r == true) {
                rpc.query({
                    model: "res.users",
                    method: "delete_backup_file",
                    args: [sub_folder, file_name],
                }).then(function (result) {
                    // console.log(result);
                    // alert(file_name + ' deleted!!! consider to refresh UI');
                    self.$el.find('.folder-item[data-idx=' + parseInt($(event.currentTarget).data('p')) + ']').click();
                });
            }
        },
        delete_folder: function (event) {
            var self = this;
            var sub_folder = self.folder_list[parseInt($(event.currentTarget).data('fid'), 10)];

            var r = confirm('Do you really want to delete ' + sub_folder + ' and all its content');
            if (r == true) {
                rpc.query({
                    model: "res.users",
                    method: "delete_backup_folder",
                    args: [sub_folder],
                }).then(function (result) {
                    // alert(sub_folder + ' deleted!!! consider to refresh UI');
                    self.restart();
                });
            }

        },
        init_display: function () {
            var self = this;
            self.$el.find('.folder-item').first().click();
        },
        restart: function () {
            var self = this;
            self.$el.empty();
            self.start();
        },
        sort_records: function (e) {
            var self = this;
            e.stopPropagation();
            var $column = $(e.currentTarget);
            var folder = self.folder_list[parseInt($column.data('p'), 10)];
            if ($column.hasClass("o-sort-down") || $column.hasClass("o-sort-up")) {
                $column.toggleClass("o-sort-up o-sort-down");
            } else {
                $column.addClass("o-sort-down");
            }
            $column.siblings('.o_column_sortable').removeClass("o-sort-up o-sort-down");

            var reverse = true;
            if ($column.hasClass("o-sort-down")) {
                reverse = false;
            }

            rpc.query({
                model: "res.users",
                method: "get_backupspath_subfolder_content",
                args: [folder, true],
            }).then(function (result) {
                self.$el.find('.folder-content-list-group').empty().append(QWeb.render('UserDataPathExplorer_FileTable', {
                    'file_list': result,
                    'folder': parseInt($column.data('p'), 10),
                    'current_folder': folder
                }));
            });
            return true;

        }
    });

    core.action_registry.add(
        'c1_project_dev.user_backups_explorer', UserDataPathExplorer
    );

    return ModulesFilter;


    var SearchImport = dialogs.SelectCreateDialog.extend({
        init: function (parent, options) {
            options = options || {};
            options.dialogClass = options.dialogClass || '' + ' o_act_window';

            this._super(parent, $.extend(true, {}, options));

            this.res_model = 'project.task';
            // this.domain = options.domain || [];
            // this.context = options.context || {};
            this.options = _.extend(this.options || {}, options || {});

            // FIXME: remove this once a dataset won't be necessary anymore to interact
            // with data_manager and instantiate views
            this.dataset = new data.DataSet(this, this.res_model, this.context);
            this.open();
        }
    });

    core.action_registry.add(
        'c1_project_dev.search_import', SearchImport
    );

});